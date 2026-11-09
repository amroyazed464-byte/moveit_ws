#!/usr/bin/env python3
"""ROS navigation/safety adapter and bounded offline HTTP operator interface."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import queue
import re
import signal
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.clock import Clock, ClockType
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Path as NavPath
from nav2_msgs.action import NavigateToPose
from sensor_msgs.msg import LaserScan
from lifecycle_msgs.srv import GetState
from tf2_ros import Buffer, TransformListener
from heritage_tour.guide_logic import GuideSession
from heritage_tour.scene import SceneBridge
from heritage_tour.voice_pack import cantonese_audio_url
from heritage_tour.runtime_paths import event_log_path


PUBLIC={'visitors','start','pause','resume','repeat','skip','next','end','question','quiz_answer',
        'recover','manual','speech_done','speech_started','speech_aborted','scenario','language'}
SCENARIOS={'clear','static_obstacle','crossing','visitor_lost','localization_lost','battery_low','unclear'}


class TourRuntime(Node):
    def __init__(self):
        super().__init__('heritage_tour_runtime')
        self.declare_parameter('port',8765)
        self.share=Path(get_package_share_directory('heritage_tour'))
        self.content=json.loads((self.share/'config/content.json').read_text(encoding='utf-8'))
        self.session=GuideSession(self.content)
        self.scene=SceneBridge()
        self.requests=queue.Queue()
        self.lock=threading.Lock();self.view={}
        self.nav=ActionClient(self,NavigateToPose,'navigate_to_pose')
        self.lifecycle=self.create_client(GetState,'/bt_navigator/get_state')
        self.nav_active=False;self.lifecycle_future=None;self.last_lifecycle_check=0.
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.pose=None;self.localization_ok=False;self.ready=False
        self.last_scan=0.;self.front=None;self.nearest=None
        self.nav_cmd=Twist();self.last_cmd=0.
        self.active_goal=None;self.goal_epoch=0;self.current_effect=None
        self.navigation={'status':'initializing','distance_remaining':None,'path':[]}
        self.injections=set();self.battery=85
        self.speech_deadline=None;self.speech_id=None
        self.speech_client_until=None;self.speech_client_id=None
        self.pending_visitors=False
        self.zone_heat={z['id']:0 for z in self.content['zones']}
        self.last_animation=0.;self.scene_initialized=False;self.scene_requested=False
        self.human_help=None;self.safety_reason='正在等待雷达、定位与导航就绪'
        self.covariance=None;self.tour_started=False
        self.publisher=self.create_publisher(Twist,'/heritage_robot/cmd_vel',10)
        self.create_subscription(Twist,'/nav2_cmd_vel',self._velocity,10)
        self.create_subscription(LaserScan,'/scan',self._scan,qos_profile_sensor_data)
        self.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',self._amcl,10)
        self.create_subscription(NavPath,'/plan',self._path,10)
        self.log_path=event_log_path()
        self.log_path.parent.mkdir(parents=True,exist_ok=True)
        self.wall_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.1,self.tick,clock=self.wall_clock)
        try:self.http=self._http(int(self.get_parameter('port').value))
        except OSError:
            self.scene.close()
            raise
        self.get_logger().info(f'Offline guide console: http://0.0.0.0:{self.http.server_port}')

    def _velocity(self,msg):self.nav_cmd=msg;self.last_cmd=time.monotonic()

    def _scan(self,msg):
        self.last_scan=time.monotonic()
        valid=[r for r in msg.ranges if math.isfinite(r) and r>=msg.range_min]
        frontal=[r for i,r in enumerate(msg.ranges) if abs(msg.angle_min+i*msg.angle_increment)<.45 and math.isfinite(r) and r>=msg.range_min]
        self.nearest=min(valid) if valid else None
        self.front=min(frontal) if frontal else None

    def _amcl(self,msg):self.covariance=float(max(msg.pose.covariance[0],msg.pose.covariance[7]))
    def _path(self,msg):self.navigation['path']=[{'x':p.pose.position.x,'y':p.pose.position.y} for p in msg.poses[::3]]

    def _locate(self):
        try:
            transform=self.tf.lookup_transform('map','base_link',Time())
            p=transform.transform.translation;q=transform.transform.rotation
            age=(self.get_clock().now().nanoseconds-(transform.header.stamp.sec*10**9+transform.header.stamp.nanosec))/1e9
            self.pose={'x':p.x,'y':p.y,'yaw':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))}
            self.localization_ok=bool(age<3 and 'localization_lost' not in self.injections and (self.covariance is None or self.covariance<1.))
        except Exception:self.localization_ok=False

    def _cancel(self):
        self.goal_epoch+=1
        if self.active_goal:self.active_goal.cancel_goal_async()
        self.active_goal=None;self.current_effect=None
        self.nav_cmd=Twist();self.last_cmd=0.
        self.navigation['status']='stopped'
        self.publisher.publish(Twist())

    def _navigate(self,effect):
        if not self.ready:
            self.apply({'type':'fault','kind':'localization_lost'});return
        self.goal_epoch+=1;epoch=self.goal_epoch
        self.current_effect=effect
        pose=PoseStamped();pose.header.frame_id='map';pose.header.stamp=self.get_clock().now().to_msg()
        x,y,yaw=effect['pose'];pose.pose.position.x=float(x);pose.pose.position.y=float(y)
        pose.pose.orientation.z=math.sin(yaw/2);pose.pose.orientation.w=math.cos(yaw/2)
        goal=NavigateToPose.Goal();goal.pose=pose
        self.navigation.update(status='navigating',target=effect['zone_id'],distance_remaining=None)
        def feedback(message):
            if epoch==self.goal_epoch:self.navigation['distance_remaining']=float(message.feedback.distance_remaining)
        future=self.nav.send_goal_async(goal,feedback_callback=feedback)
        def accepted(future):
            handle=future.result()
            if epoch!=self.goal_epoch:
                if handle.accepted:handle.cancel_goal_async()
                return
            if not handle.accepted:
                self.apply({'type':'fault','kind':'route_blocked'});return
            self.active_goal=handle
            def finished(result):
                if epoch!=self.goal_epoch:return
                self.active_goal=None
                status=result.result().status
                if status==4:
                    self.navigation['status']='arrived';self.nav_cmd=Twist();self.publisher.publish(Twist())
                    event={'type':'home_arrived' if effect['zone_id']=='home' else 'arrived',
                           'zone_id':effect['zone_id'],'navigation_id':effect.get('navigation_id')}
                    # Ground truth is used only as a simulation acceptance guard, not localization input.
                    actual=self.scene.robot
                    if actual and math.hypot(actual['x']-x,actual['y']-y)>.55:
                        self.apply({'type':'fault','kind':'localization_lost'})
                    else:
                        if effect['zone_id'] in self.zone_heat:self.zone_heat[effect['zone_id']]+=1
                        self.apply(event)
                else:self.apply({'type':'fault','kind':'route_blocked'})
            handle.get_result_async().add_done_callback(finished)
        future.add_done_callback(accepted)

    def apply(self,event):
        effects=self.session.apply(event)
        for effect in effects:
            kind=effect['type']
            if kind=='navigate':self._navigate(effect)
            elif kind=='cancel_navigation':
                self._cancel();self.speech_deadline=None;self.speech_client_until=None;self.speech_client_id=None
            elif kind=='speak':
                self.speech_id=effect['id']
                self.speech_client_until=None;self.speech_client_id=None
                units=len(effect['text']) if effect['language']!='en' else len(effect['text'].split())*3
                self.speech_deadline=time.monotonic()+max(5.,min(180.,units/4.0))
            elif kind=='theme':
                state=self.session.state
                expression='alert' if state in ('FAULT','MANUAL') else 'waiting' if state in ('PAUSED','QUIZ') else 'happy'
                color='red' if state in ('FAULT','MANUAL') else 'blue' if state in ('NAVIGATING','RETURNING') else 'gold'
                zone='fault' if state=='FAULT' else 'manual' if state=='MANUAL' else 'return' if state in ('RETURNING','COMPLETE') else None if state in ('IDLE','WELCOMING') else effect.get('zone_id')
                self.scene.submit('theme',expression=expression,color=color,zone_id=zone)
            elif kind=='human_help':self.human_help=effect['reason']
            elif kind=='log':
                with self.log_path.open('a',encoding='utf-8') as f:f.write(json.dumps(effect['record'],ensure_ascii=False)+'\n')

    def command(self,event):
        kind=event.get('type')
        if kind not in PUBLIC:raise ValueError('此接口不接受内部导航/定位事件')
        if kind in ('speech_started','speech_aborted'):
            speech=self.session.speech
            if speech and event.get('speech_id')==speech['id']:
                if kind=='speech_started':
                    self.speech_client_id=speech['id'];self.speech_client_until=time.monotonic()+8.
                    self.speech_deadline=None
                else:
                    self.speech_client_until=None;self.speech_client_id=None
                    units=len(speech['text']) if speech['language']!='en' else len(speech['text'].split())*3
                    self.speech_deadline=time.monotonic()+max(5.,min(180.,units/4.0))
            return
        if kind=='speech_done' and self.session.speech and event.get('speech_id')==self.session.speech['id']:
            self.speech_deadline=None;self.speech_client_until=None;self.speech_client_id=None
        if kind=='visitors':
            if self.pending_visitors:raise ValueError('正在布置仿真游客，请等待完成')
            if self.session.state not in ('IDLE','WELCOMING','COMPLETE'):raise ValueError('请先结束当前导览再更换游客')
            count=event.get('count')
            if isinstance(count,bool) or count not in (0,1,3):raise ValueError('请选择0、1或3名模拟游客')
            self.pending_visitors=True;self.scene.submit('visitors',count=count);return
        if kind=='scenario':
            name=event.get('name')
            if name not in SCENARIOS:raise ValueError('未知仿真场景')
            self.scene.submit('scenario',name=name)
            if name=='clear':
                self.injections.clear();self.battery=85
            elif name in ('localization_lost','visitor_lost','battery_low','unclear'):
                self.injections.add(name)
                if name=='battery_low':self.battery=12
                self.apply({'type':'fault','kind':name,'simulated':True})
            return
        if kind in ('start','resume','next','skip','end') and not self.ready:
            raise ValueError('雷达、定位或导航尚未就绪，机器人保持停止')
        if kind in ('start','resume','next','skip','end') and self.injections:
            raise ValueError('仿真故障尚未清除，请先恢复正常场景并确认安全')
        if kind=='start':
            if self.pending_visitors:raise ValueError('正在布置仿真游客，尚不能开始导览')
            if not self.scene.visitors:raise ValueError('请先选择单人或多人到访，完成迎宾')
            self.tour_started=True
        if kind=='question' and len(str(event.get('text','')))>600:raise ValueError('问题过长，请简述')
        if kind=='recover':
            if self.injections:raise ValueError('请先清除仿真故障并确认安全，再恢复')
            if not self.ready:raise ValueError('实际定位/传感器未恢复，禁止继续')
            self.human_help=None
        self.apply(event)

    def tick(self):
        now=time.monotonic();self._locate()
        if self.lifecycle_future is not None and now-self.last_lifecycle_check>3:
            pending=self.lifecycle_future;self.lifecycle_future=None;self.nav_active=False
            pending.cancel()
        if now-self.last_lifecycle_check>2 and self.lifecycle.service_is_ready() and self.lifecycle_future is None:
            self.last_lifecycle_check=now
            self.lifecycle_future=self.lifecycle.call_async(GetState.Request())
            def lifecycle_result(future):
                if self.lifecycle_future is not future:return
                try:self.nav_active=future.result().current_state.id==3
                except Exception:self.nav_active=False
                self.lifecycle_future=None
            self.lifecycle_future.add_done_callback(lifecycle_result)
        scan_fresh=now-self.last_scan<2.5
        self.ready=bool(self.localization_ok and scan_fresh and self.nav_active and self.nav.server_is_ready() and self.scene.robot and now-self.scene.robot_stamp<3. and self.scene.motion_ok and self.scene.transport.poll() is None)
        if self.ready and self.navigation['status']=='initializing':self.navigation['status']='ready'
        if self.ready and not self.scene_requested:
            self.scene_requested=True;self.scene.submit('initialize')
        while not self.scene.notifications.empty():
            event=self.scene.notifications.get_nowait()
            if event['type']=='visitors_ready':
                self.pending_visitors=False;self.apply({'type':'visitor','count':event['count']})
            elif event['type']=='scene_ready':
                self.scene_initialized=True;self.scene.submit('theme')
            elif event['type']=='scene_error':
                self.get_logger().warning(f"Scene {event.get('operation')}: {event['error']}")
                if event.get('operation')=='visitors':
                    self.pending_visitors=False;self.apply({'type':'fault','kind':'scene_update_failed'})
                elif event.get('operation')=='visitor_pose' and self.session.state in ('NAVIGATING','RETURNING'):
                    self.apply({'type':'fault','kind':'scene_update_failed'})
        while not self.requests.empty():
            event,result,done=self.requests.get_nowait()
            try:self.command(event);result.update(ok=True)
            except (ValueError,TypeError,KeyError) as exc:result.update(ok=False,error=str(exc))
            finally:done.set()
        moving=self.session.state in ('NAVIGATING','RETURNING')
        if moving and (not self.scene.motion_ok or self.scene.transport.poll() is not None):
            self.apply({'type':'fault','kind':'scene_update_failed'});moving=False
        if moving and not self.localization_ok:
            self.apply({'type':'fault','kind':'localization_lost'});moving=False
        if moving and not scan_fresh:
            self.apply({'type':'fault','kind':'sensor_stale'});moving=False
        if moving and self.scene.freeze_visitors and self.scene.robot and any(math.hypot(p['x']-self.scene.robot['x'],p['y']-self.scene.robot['y'])>4 for p in self.scene.visitors):
            self.apply({'type':'fault','kind':'visitor_lost'});moving=False
        output=Twist();self.safety_reason='已停车待命'
        if moving and self.ready and now-self.last_cmd<1.0:
            maximum=.18 if len(self.scene.visitors)>1 else .27
            output.linear.x=max(-.12,min(maximum,self.nav_cmd.linear.x))
            output.angular.z=max(-.65,min(.65,self.nav_cmd.angular.z))
            self.safety_reason='多人慢行' if len(self.scene.visitors)>1 else '正常导览'
            if self.nearest is not None and self.nearest<.36:
                output=Twist();self.safety_reason='近距离障碍，安全停车'
            elif output.linear.x>0 and self.front is not None:
                if self.front<.62:output.linear.x=0.;self.safety_reason='等待前方行人/障碍'
                elif self.front<1.0:output.linear.x=min(output.linear.x,.12);self.safety_reason='前方有人/障碍，减速'
        elif moving:self.safety_reason='等待新鲜的定位、雷达或控制指令'
        self.publisher.publish(output)
        if self.speech_client_until and now>=self.speech_client_until:
            self.speech_client_until=None;self.speech_client_id=None
            self.apply({'type':'pause'})
            self.session.message='朗读连接中断，导览已暂停。字幕保留，请确认后继续。'
        if self.speech_deadline and now>=self.speech_deadline:
            self.speech_deadline=None;self.apply({'type':'speech_done','speech_id':self.speech_id})
        if now-self.last_animation>.5:
            self.scene.animate(now,following=moving);self.last_animation=now
        view=self.session.snapshot()
        if view['speech']:
            view['speech']['audio_url']=cantonese_audio_url(self.share,view['speech'])
        truth=self.scene.robot
        error=math.hypot(self.pose['x']-truth['x'],self.pose['y']-truth['y']) if self.pose and truth else None
        view.update(ready=self.ready,robot_pose=deepcopy(self.pose or truth),world_pose=deepcopy(truth),
                    pending_visitors=self.pending_visitors,operation={'zone_heat':dict(self.zone_heat)},
                    media={'client_active':self.speech_client_until is not None,'subtitle_fallback':self.speech_client_until is None},
                    navigation=deepcopy(self.navigation),visitors=deepcopy(self.scene.visitors),route=self.content['zones'],
                    sources=self.content.get('sources',[]),map={'width':35.4,'height':22.},human_help=self.human_help,
                    safety={'reason':self.safety_reason,'battery':self.battery,'battery_simulated':True,
                            'localization_ok':self.localization_ok,'localization_error':error,'scan_fresh':scan_fresh,
                            'front_distance':self.front,'speed':output.linear.x,'injections':sorted(self.injections)},
                    scene_linkage={'ready':self.scene_initialized,'ok':self.scene.linkage_ok,'motion_ok':self.scene.motion_ok,'transport_alive':self.scene.transport.poll() is None,'error':self.scene.last_error})
        with self.lock:self.view=view

    def _http(self,port):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,status,body,content_type='application/json; charset=utf-8'):
                self.send_response(status);self.send_header('Content-Type',content_type)
                self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_GET(self):
                path=self.path.split('?',1)[0]
                if path=='/api/state':
                    with owner.lock:body=json.dumps(owner.view,ensure_ascii=False,allow_nan=False).encode()
                    self.send(200,body)
                elif path=='/api/map.png':self.send(200,(owner.share/'maps/map.png').read_bytes(),'image/png')
                elif re.fullmatch(r'/audio/yue/(?:[a-f0-9]{64}|preview)\.mp3',path):
                    clip=owner.share/'voices/yue'/path.rsplit('/',1)[1]
                    if clip.is_file():self.send(200,clip.read_bytes(),'audio/mpeg')
                    else:self.send(404,b'{"ok":false}')
                elif path in ('/','/display','/index.html'):self.send(200,(owner.share/'web/index.html').read_bytes(),'text/html; charset=utf-8')
                else:self.send(404,b'{"ok":false}')
            def do_POST(self):
                if self.path!='/api/command':self.send(404,b'{"ok":false}');return
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=8192 or self.headers.get_content_type()!='application/json':raise ValueError('Invalid request')
                    event=json.loads(self.rfile.read(length));result={};done=threading.Event()
                    if not isinstance(event,dict):raise ValueError('Expected object')
                    owner.requests.put((event,result,done))
                    if not done.wait(3):result={'ok':False,'error':'运行时繁忙，请稍后重试'}
                    self.send(200 if result.get('ok') else 400,json.dumps(result,ensure_ascii=False).encode())
                except (ValueError,TypeError) as exc:self.send(400,json.dumps({'ok':False,'error':str(exc)}).encode())
        server=ThreadingHTTPServer(('0.0.0.0',port),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        return server

    def close(self):
        self._cancel();self.scene.close();self.http.shutdown()


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT,signal.default_int_handler)
    signal.signal(signal.SIGTERM,signal.default_int_handler)
    node=TourRuntime()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        node.close();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
