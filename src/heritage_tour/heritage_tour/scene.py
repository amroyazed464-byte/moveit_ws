"""Gazebo scene adapter. Simulated visitor inputs are kept explicit."""
from collections import deque
import json
import math
from pathlib import Path
import queue
import re
import subprocess
import threading
import time


class SceneBridge:
    def __init__(self):
        from ament_index_python.packages import get_package_prefix
        self.commands=queue.Queue()
        self.notifications=queue.Queue()
        self.robot=None
        self.robot_stamp=0.
        self.visitors=[]
        self.history=deque(maxlen=4000)
        self.crossing_until=0.
        self.freeze_visitors=False
        self.last_error=''
        self.linkage_ok=False
        self.motion_ok=True
        self.visual_ids={}
        self.closed=False
        self.reader=None
        self.latest_poses=None
        helper=Path(get_package_prefix('heritage_tour'))/'lib/heritage_tour/scene_transport'
        self.screen_plugin=helper.parent.parent/'libheritage_tour_screens.so'
        self.transport=subprocess.Popen([str(helper)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL,text=True,bufsize=1)
        threading.Thread(target=self._read_poses,daemon=True).start()
        threading.Thread(target=self._work,daemon=True).start()

    def submit(self,operation,**kwargs):
        self.commands.put((operation,kwargs))

    def _service(self,name,request_type,request,required=True):
        timeout=8000 if name=='create' else 3000
        result=self._request(name,request_type,request,'gz.msgs.Boolean',timeout)
        ok=result.startswith('OK\t') and 'data: true' in result
        if required and not ok:
            raise RuntimeError(f'{name}: '+result.strip()[:180])
        return ok

    def _request(self,name,request_type,request,response_type,timeout):
        self.transport.stdin.write('\n'.join(['/world/heritage_hall/'+name,request_type,
                                               response_type,str(timeout),request])+'\n')
        self.transport.stdin.flush()
        result=self.transport.stdout.readline()
        if not result:raise RuntimeError('Gazebo scene transport disconnected')
        return result

    def _create(self,sdf):
        return self._service('create','gz.msgs.EntityFactory','sdf: '+json.dumps(sdf))

    def _remove(self,name):
        self._service('remove','gz.msgs.Entity','name: '+json.dumps(name)+' type: MODEL',False)

    @staticmethod
    def person(name,x,y,color='0.18 0.42 0.56 1'):
        return f'''<sdf version="1.9"><model name="{name}"><static>true</static><pose>{x} {y} 0 0 0 0</pose><link name="body">
<collision name="contact"><pose>0 0 .87 0 0 0</pose><geometry><cylinder><radius>.22</radius><length>1.74</length></cylinder></geometry></collision>
<visual name="coat"><pose>0 0 .88 0 0 0</pose><geometry><cylinder><radius>.2</radius><length>1.12</length></cylinder></geometry><material><ambient>{color}</ambient><diffuse>{color}</diffuse></material></visual>
<visual name="head"><pose>0 0 1.60 0 0 0</pose><geometry><sphere><radius>.145</radius></sphere></geometry><material><ambient>.78 .62 .44 1</ambient><diffuse>.78 .62 .44 1</diffuse></material></visual>
<visual name="legs"><pose>0 0 .19 0 0 0</pose><geometry><box><size>.27 .29 .38</size></box></geometry><material><ambient>.18 .19 .22 1</ambient><diffuse>.18 .19 .22 1</diffuse></material></visual>
</link></model></sdf>'''

    def _initialize(self):
        self._service('entity/system/add','gz.msgs.EntityPlugin_V',
                      'entity: {name: "heritage_hall", type: WORLD}, plugins: {filename: '+json.dumps(str(self.screen_plugin))+', name: "heritage_tour::ScreenSystem"}')
        self._remove('tour_display')
        self._create('''<sdf version="1.9"><model name="tour_display"><static>true</static><pose>-3 10.55 2.9 0 0 0</pose><link name="body">
<visual name="frame"><geometry><box><size>3.2 .10 1.8</size></box></geometry><material><ambient>.08 .09 .11 1</ambient><diffuse>.08 .09 .11 1</diffuse></material></visual>
<visual name="screen"><pose>0 -.06 0 0 0 0</pose><geometry><mesh><uri>model://heritage_guide/meshes/tour_display.dae</uri></mesh></geometry><material><diffuse>1 1 1 1</diffuse><pbr><metal><albedo_map>model://heritage_guide/materials/textures/tour_welcome.png</albedo_map><metalness>0</metalness><roughness>.6</roughness></metal></pbr></material></visual>
</link></model></sdf>''')
        self.notifications.put({'type':'scene_ready'})

    def _set_visitors(self,count):
        count=max(0,min(3,int(count)))
        self.visitors=[]
        for i in range(3):self._remove(f'tour_visitor_{i}')
        people=[]
        robot=self.robot or {'x':-13.27,'y':-7.73,'yaw':math.pi/2}
        for i in range(count):
            distance=1.05+i*.60
            x=robot['x']-distance*math.cos(robot['yaw'])
            y=robot['y']-distance*math.sin(robot['yaw'])
            name=f'tour_visitor_{i}'
            self._create(self.person(name,x,y))
            people.append({'id':name,'x':x,'y':y,'yaw':robot['yaw']})
        self.visitors=people
        self.motion_ok=True
        self.freeze_visitors=False
        self.history.clear()
        self.notifications.put({'type':'visitors_ready','count':count})

    def _theme(self,expression='happy',color='gold',zone_id=None):
        if expression not in ('happy','waiting','alert','thinking'):expression='happy'
        zone=zone_id if zone_id in ('overview','craft','masterpieces','history','interactive','return','manual','fault') else 'welcome'
        colors={'gold':(1.,.65,.25),'blue':(.15,.6,1.),'red':(1.,.15,.1),'green':(.15,.9,.35)}
        r,g,b=colors.get(color,colors['gold'])
        def texture(name,path):
            self._service('tour_texture','gz.msgs.Visual',f'name: "{name}", material: {{diffuse: {{r: 1,g: 1,b: 1,a: 1}}, pbr: {{type: METAL,albedo_map: "model://heritage_guide/materials/textures/{path}.png",roughness: .6}}}}')
        texture('heritage_guide::base_link::face','tour_face_'+expression)
        texture('heritage_guide::base_link::tablet_display','tour_'+zone)
        texture('tour_display::body::screen','tour_'+zone)
        entity_id=self._visual_id('heritage_guide::base_link::bottom_light')
        self._service('visual_config','gz.msgs.Visual',f'id:{entity_id},material: {{diffuse: {{r:{r},g:{g},b:{b},a:1}},emissive: {{r:{r},g:{g},b:{b},a:1}}}}')
        self.linkage_ok=True
        self.last_error=''

    def _visual_id(self,name):
        if name not in self.visual_ids:
            result=self._request('scene/graph','gz.msgs.Empty','','gz.msgs.StringMsg',5000)
            if not result.startswith('OK\tdata:'):
                raise RuntimeError('scene/graph: '+result.strip()[:180])
            graph=json.loads(result.removeprefix('OK\t').strip().removeprefix('data: ').strip())
            labels={int(entity):label for entity,label in re.findall(r'(\d+) \[label="(.*?) \(\d+\)"\];',graph)}
            parents={int(child):int(parent) for parent,child in re.findall(r'(\d+) -> (\d+) \[label=1\];',graph)}
            for entity in labels:
                parts=[];current=entity
                while current in parents:
                    parts.append(labels[current]);current=parents[current]
                self.visual_ids['::'.join(reversed(parts))]=entity
        if name not in self.visual_ids:raise RuntimeError('Gazebo visual not yet available: '+name)
        return self.visual_ids[name]

    def _scenario(self,name):
        if name=='clear':
            self._remove('tour_static_obstacle');self._remove('tour_crossing_visitor')
            self.crossing_until=0.;self.freeze_visitors=False
        elif name=='static_obstacle' and self.robot:
            p=self.robot;x=p['x']+1.7*math.cos(p['yaw']);y=p['y']+1.7*math.sin(p['yaw'])
            self._remove('tour_static_obstacle')
            self._create(f'''<sdf version="1.9"><model name="tour_static_obstacle"><static>true</static><pose>{x} {y} 0 0 0 0</pose><link name="body"><collision name="contact"><pose>0 0 .9 0 0 0</pose><geometry><box><size>.7 .7 1.8</size></box></geometry></collision><visual name="barrier"><pose>0 0 .9 0 0 0</pose><geometry><box><size>.7 .7 1.8</size></box></geometry><material><ambient>.8 .3 .12 1</ambient><diffuse>.8 .3 .12 1</diffuse></material></visual></link></model></sdf>''')
        elif name=='crossing' and self.robot:
            self._remove('tour_crossing_visitor')
            p=self.robot;self.cross_origin=dict(p);self.crossing_until=time.monotonic()+14
            self._create(self.person('tour_crossing_visitor',p['x']+1.5,p['y']+1.5,'0.76 .35 .25 1'))
        elif name=='visitor_lost':self.freeze_visitors=True

    def animate(self,now,following=True):
        robot=self.robot
        if not robot:return
        if not self.history or math.hypot(robot['x']-self.history[-1][0],robot['y']-self.history[-1][1])>.035:
            self.history.append((robot['x'],robot['y'],robot['yaw']))
        poses=[]
        if following and not self.freeze_visitors:
            for i,person in enumerate(self.visitors):
                remaining=1.25+i*.75
                last=(robot['x'],robot['y'],robot['yaw'])
                target=None
                for previous in reversed(self.history):
                    remaining-=math.dist(last[:2],previous[:2]);last=previous
                    if remaining<=0:target=previous;break
                if target:
                    poses.append(dict(person,x=target[0],y=target[1],yaw=target[2]))
        elif not self.motion_ok:
            poses.extend(dict(person) for person in self.visitors)
        if self.crossing_until:
            if now<self.crossing_until:
                p=self.cross_origin;t=(14-(self.crossing_until-now))/14
                along=1.7;side=-1.5+3*t
                poses.append({'id':'tour_crossing_visitor','x':p['x']+along*math.cos(p['yaw'])-side*math.sin(p['yaw']),
                              'y':p['y']+along*math.sin(p['yaw'])+side*math.cos(p['yaw']),'yaw':p['yaw']+math.pi/2})
            else:
                self.crossing_until=0.;self.submit('remove',name='tour_crossing_visitor')
        self.latest_poses=poses

    def _work(self):
        while not self.closed:
            try:
                try:operation,args=self.commands.get(timeout=.25)
                except queue.Empty:operation,args=None,{}
                if operation=='initialize':self._initialize()
                elif operation=='visitors':self._set_visitors(**args)
                elif operation=='theme':self._theme(**args)
                elif operation=='scenario':self._scenario(**args)
                elif operation=='remove':self._remove(**args)
                poses=self.latest_poses;self.latest_poses=None
                if poses:
                    operation='visitor_pose'
                    request=' '.join('pose: {name: %s,position: {x:%.6f,y:%.6f,z:0},orientation: {z:%.8f,w:%.8f}}'
                                     % (json.dumps(p['id']),p['x'],p['y'],math.sin(p['yaw']/2),math.cos(p['yaw']/2)) for p in poses)
                    self._service('set_pose_vector','gz.msgs.Pose_V',request)
                    for pose in poses:
                        for person in self.visitors:
                            if person['id']==pose['id']:person.update(pose)
                    self.motion_ok=True
            except Exception as exc:
                self.last_error=str(exc);self.linkage_ok=False
                if operation=='visitor_pose':self.motion_ok=False
                self.notifications.put({'type':'scene_error','operation':operation,'error':str(exc)})

    def _read_poses(self):
        decoder=json.JSONDecoder()
        while not self.closed:
            try:
                self.reader=subprocess.Popen(['gz','topic','-e','-t','/world/heritage_hall/dynamic_pose/info','--json-output'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
                buffer=''
                for line in self.reader.stdout:
                    if self.closed:break
                    buffer+=line
                    try:data,end=decoder.raw_decode(buffer.lstrip())
                    except json.JSONDecodeError:continue
                    buffer=buffer.lstrip()[end:].lstrip()
                    for pose in data.get('pose',[]):
                        if pose.get('name')!='heritage_guide':continue
                        p=pose.get('position',{});q=pose.get('orientation',{})
                        yaw=math.atan2(2*(q.get('w',1)*q.get('z',0)+q.get('x',0)*q.get('y',0)),1-2*(q.get('y',0)**2+q.get('z',0)**2))
                        self.robot={'x':p.get('x',0.),'y':p.get('y',0.),'yaw':yaw}
                        self.robot_stamp=time.monotonic()
            except Exception as exc:self.last_error=str(exc)
            time.sleep(.5)

    def close(self):
        self.closed=True
        if self.reader:self.reader.terminate()
        self.transport.terminate()
