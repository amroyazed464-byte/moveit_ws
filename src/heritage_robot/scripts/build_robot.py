#!/usr/bin/env python3
"""Generate the reference-inspired guide robot using local mesh and texture assets."""
from pathlib import Path
import math
import xml.etree.ElementTree as E
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / 'models/heritage_guide'
WHITE = '0.91 0.89 0.83 1'
GOLD = '0.66 0.43 0.23 1'
BLACK = '0.015 0.022 0.03 1'


def tag(parent, key, value=None, **attrs):
    node = E.SubElement(parent, key, attrs)
    if value is not None:
        node.text = str(value)
    return node


def mesh(name, vertices, normals, uv, triangles):
    """COLLADA with explicit vertex normals and UVs for Ogre2."""
    doc = E.Element('COLLADA', xmlns='http://www.collada.org/2005/11/COLLADASchema', version='1.4.1')
    asset = tag(doc, 'asset')
    tag(asset, 'created', '2026-11-08T00:00:00'); tag(asset, 'modified', '2026-11-08T00:00:00')
    tag(asset, 'unit', meter='1', name='meter'); tag(asset, 'up_axis', 'Z_UP')
    geo = tag(tag(doc, 'library_geometries'), 'geometry', id='geometry')
    body = tag(geo, 'mesh')
    for key, values, params in [('pos', vertices, 'XYZ'), ('norm', normals, 'XYZ'), ('uv', uv, 'ST')]:
        source = tag(body, 'source', id=key)
        tag(source, 'float_array', ' '.join(f'{v:.7f}' for row in values for v in row), id=key+'-array', count=str(len(values)*len(params)))
        accessor = tag(tag(source, 'technique_common'), 'accessor', source='#'+key+'-array', count=str(len(values)), stride=str(len(params)))
        for p in params:
            tag(accessor, 'param', name=p, type='float')
    tag(tag(body, 'vertices', id='verts'), 'input', semantic='POSITION', source='#pos')
    faces = tag(body, 'triangles', count=str(len(triangles)))
    for i, (semantic, source) in enumerate([('VERTEX', '#verts'), ('NORMAL', '#norm'), ('TEXCOORD', '#uv')]):
        tag(faces, 'input', semantic=semantic, source=source, offset=str(i))
    tag(faces, 'p', ' '.join(str(index) for tri in triangles for index in tri for _ in range(3)))
    scene = tag(tag(doc, 'library_visual_scenes'), 'visual_scene', id='Scene')
    tag(tag(scene, 'node', id='node'), 'instance_geometry', url='#geometry')
    tag(tag(doc, 'scene'), 'instance_visual_scene', url='#Scene')
    E.ElementTree(doc).write(ROOT / 'meshes' / (name+'.dae'), encoding='utf-8', xml_declaration=True)


def surface(name, rows, columns, point, normal, texcoord):
    vertices, normals, uv, triangles = [], [], [], []
    for i in range(rows+1):
        for j in range(columns+1):
            vertices.append(point(i/rows, j/columns))
            n = normal(i/rows, j/columns)
            length = math.sqrt(sum(v*v for v in n))
            normals.append(tuple(v/length for v in n))
            uv.append(texcoord(i/rows, j/columns))
    for i in range(rows):
        for j in range(columns):
            a = i*(columns+1)+j
            triangles.extend([(a, a+1, a+columns+2), (a, a+columns+2, a+columns+1)])
    mesh(name, vertices, normals, uv, triangles)


def lathe(name, profile):
    vertices, normals, uv, triangles = [], [], [], []
    segments = 64
    for i, (z, radius) in enumerate(profile):
        before, after = profile[max(0, i-1)], profile[min(len(profile)-1, i+1)]
        dz, dr = after[0]-before[0], after[1]-before[1]
        length = math.hypot(dz, dr)
        for j in range(segments+1):
            a = j*math.tau/segments
            vertices.append((radius*math.cos(a), radius*math.sin(a), z))
            normals.append((dz*math.cos(a)/length, dz*math.sin(a)/length, -dr/length))
            uv.append((j/segments, i/(len(profile)-1)))
    for i in range(len(profile)-1):
        for j in range(segments):
            a=i*(segments+1)+j
            triangles.extend([(a,a+1,a+segments+2),(a,a+segments+2,a+segments+1)])
    mesh(name,vertices,normals,uv,triangles)


def artwork():
    font_path = next((p for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'C:/Windows/Fonts/msyh.ttc'] if Path(p).exists()), None)
    def font(size):
        return ImageFont.truetype(font_path,size) if font_path else ImageFont.load_default()

    face = Image.new('RGB',(768,768),'#02070d')
    d = ImageDraw.Draw(face)
    for x in (235,533):
        d.arc((x-62,260,x+62,425),185,355,fill='#345b91',width=25)
        d.arc((x-62,260,x+62,425),185,355,fill='#d9f5ff',width=12)
    d.arc((304,369,464,515),12,168,fill='#bceaff',width=12)
    for x in (199,569):
        d.ellipse((x-32,433,x+32,455),fill='#754450')
        for dx in (-17,0,17):
            d.line((x+dx,431,x+dx-5,451),fill='#efb9b0',width=5)
    face.save(ROOT/'materials/textures/face.png')

    screen = Image.new('RGB',(600,900),'#101f34')
    d=ImageDraw.Draw(screen)
    d.rounded_rectangle((18,18,582,882),radius=30,outline='#d3ae7b',width=3)
    d.text((300,89),'非遗智伴',font=font(36),fill='#e9c99e',anchor='mm')
    d.text((300,202),'欢迎来到',font=font(46),fill='#fff6e4',anchor='mm')
    d.text((300,269),'非遗展厅',font=font(59),fill='#fff6e4',anchor='mm')
    d.text((300,340),'以科技之力 · 传承非遗之美',font=font(20),fill='#c6d3de',anchor='mm')
    for points,color in [([(20,660),(130,450),(240,620),(350,480),(580,680)],'#576d85'), ([(20,730),(180,540),(290,665),(420,550),(580,730)],'#8997a1')]:
        d.polygon(points,fill=color)
    d.rectangle((195,580,410,700),fill='#b77d48')
    for y,w in [(560,280),(615,300),(680,330)]:
        d.polygon([(300-w/2,y),(300+w/2,y),(300+w/2-35,y-28),(300-w/2+35,y-28)],fill='#edc88f')
    for x in range(220,405,32):
        d.rectangle((x,590,x+12,694),fill='#5a3b2b')
    d.rounded_rectangle((110,764,490,842),radius=23,fill='#e0b783')
    d.text((300,801),'开始导览  ›',font=font(34),fill='#352a21',anchor='mm')
    screen.save(ROOT/'materials/textures/screen.png')

    skirt = Image.new('RGB',(1024,512),'#e9e4d8')
    d=ImageDraw.Draw(skirt)
    for cx,cy,r in [(280,320,80),(380,280,75),(480,340,95),(610,295,65),(700,360,90)]:
        d.arc((cx-r,cy-r,cx+r,cy+r),190,520,fill='#c09864',width=9)
        d.arc((cx-r+19,cy-r+19,cx+r-19,cy+r-19),200,510,fill='#c09864',width=4)
    d.text((512,116),'非遗智伴',font=font(49),fill='#997145',anchor='mm')
    skirt.save(ROOT/'materials/textures/clouds.png')


def build():
    for folder in ('meshes','materials/textures'):
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    artwork()
    skirt_profile=[(.045,0),(.045,.23),(.06,.28),(.08,.297),(.11,.30),(.14,.296),(.20,.282),(.30,.266),(.48,.238),(.65,.195),(.74,.15),(.76,.12),(.76,0)]
    lathe('skirt',skirt_profile)
    lathe('torso',[(.72,0),(.72,.12),(.78,.15),(.88,.195),(1.04,.215),(1.11,.19),(1.16,.12),(1.16,0)])
    surface('head',32,64,
            lambda u,v:(.174*math.sin(u*math.pi)*math.cos(v*math.tau),.18*math.sin(u*math.pi)*math.sin(v*math.tau),-.18*math.cos(u*math.pi)),
            lambda u,v:(math.sin(u*math.pi)*math.cos(v*math.tau)/.174,math.sin(u*math.pi)*math.sin(v*math.tau)/.18,-math.cos(u*math.pi)/.18),
            lambda u,v:(v,u))
    # Facing +X. UV t increases upwards; facial texture stays upright.
    surface('visor',20,32,
            lambda u,v:(.178*math.cos((u-.5)*1.65)*math.cos((v-.5)*2.05),.184*math.cos((u-.5)*1.65)*math.sin((v-.5)*2.05),.184*math.sin((u-.5)*1.65)),
            lambda u,v:(math.cos((u-.5)*1.65)*math.cos((v-.5)*2.05),math.cos((u-.5)*1.65)*math.sin((v-.5)*2.05),math.sin((u-.5)*1.65)),
            lambda u,v:(v,u))
    surface('screen',1,1,lambda u,v:(0,(v-.5)*.302,(u-.5)*.462),lambda u,v:(1,0,0),lambda u,v:(v,u))
    def skirt_radius(u):
        z=.25+.42*u
        for (a,ra),(b,rb) in zip(skirt_profile,skirt_profile[1:]):
            if a<=z<=b and b>a:
                return ra+(rb-ra)*(z-a)/(b-a)+.0015
    surface('decoration',24,40,
            lambda u,v:(skirt_radius(u)*math.cos((v-.5)*2.3),skirt_radius(u)*math.sin((v-.5)*2.3),.25+.42*u),
            lambda u,v:(math.cos((v-.5)*2.3),math.sin((v-.5)*2.3),.197),lambda u,v:(v,u))
    for name,major,minor in [('ring',.088,.005),('base_gold',.292,.014),('base_light',.302,.004)]:
        surface(name,10,64,
                lambda u,v:((major+minor*math.cos(u*math.tau))*math.cos(v*math.tau),(major+minor*math.cos(u*math.tau))*math.sin(v*math.tau),minor*math.sin(u*math.tau)),
                lambda u,v:(math.cos(u*math.tau)*math.cos(v*math.tau),math.cos(u*math.tau)*math.sin(v*math.tau),math.sin(u*math.tau)),lambda u,v:(v,u))

    sdf=E.Element('sdf',version='1.9')
    model=tag(sdf,'model',name='heritage_guide')
    tag(model,'self_collide','false')
    base=tag(model,'link',name='base_link')

    def inertia(link,mass,center,moments):
        inert=tag(link,'inertial'); tag(inert,'pose',f'0 0 {center} 0 0 0'); tag(inert,'mass',mass)
        tensor=tag(inert,'inertia')
        for key,val in zip(('ixx','iyy','izz'),moments):tag(tensor,key,val)

    inertia(base,38,.31,(3.2,3.2,1.1))

    def visual(link,name,geometry,pose='0 0 0 0 0 0',color=WHITE,texture=None,emissive=None):
        vis=tag(link,'visual',name=name); tag(vis,'pose',pose)
        geo=tag(vis,'geometry')
        if isinstance(geometry,str):tag(tag(geo,'mesh'),'uri','model://heritage_guide/meshes/'+geometry+'.dae')
        else:
            kind,values=geometry
            shape=tag(geo,kind)
            keys={'box':['size'],'cylinder':['radius','length'],'sphere':['radius']}[kind]
            for key,value in zip(keys,values):tag(shape,key,value)
        mat=tag(vis,'material'); tag(mat,'ambient',color); tag(mat,'diffuse',color)
        tag(mat,'specular','0.3 0.3 0.3 1')
        if texture:
            pbr=tag(tag(mat,'pbr'),'metal'); tag(pbr,'albedo_map','model://heritage_guide/materials/textures/'+texture+'.png')
            tag(pbr,'roughness','.45'); tag(pbr,'metalness','0')
        if emissive:tag(mat,'emissive',emissive)

    def collision(link,name,kind,values,pose,friction=1):
        col=tag(link,'collision',name=name+'_collision'); tag(col,'pose',pose)
        shape=tag(tag(col,'geometry'),kind)
        for key,value in zip({'box':['size'],'cylinder':['radius','length'],'sphere':['radius']}[kind],values):tag(shape,key,value)
        ode=tag(tag(tag(col,'surface'),'friction'),'ode'); tag(ode,'mu',friction); tag(ode,'mu2',friction)

    collision(base,'base_contact','cylinder',(.29,.14),'0 0 .17 0 0 0')
    collision(base,'body_contact','cylinder',(.215,.88),'0 0 .74 0 0 0')
    collision(base,'head_contact','sphere',(.18,),'0 0 1.37 0 0 0')
    collision(base,'tablet_contact','box',('.045 .35 .52',),'0.225 0 .94 0 -.18 0')
    for x in (-.21,.21):
        collision(base,f'caster_{x}','sphere',(.032,),f'{x} 0 .032 0 0 0',0)
        visual(base,f'caster_visual_{x}',('sphere',(.032,)),f'{x} 0 .032 0 0 0',BLACK)
    visual(base,'skirt','skirt')
    visual(base,'torso','torso')
    visual(base,'cloud_motif','decoration',color='1 1 1 1',texture='clouds')
    visual(base,'waist_ring',('cylinder',(.151,.035)),'0 0 .745 0 0 0',GOLD)
    visual(base,'neck',('cylinder',(.055,.09)),'0 0 1.19 0 0 0',GOLD)
    visual(base,'head_shell','head','0 0 1.37 0 0 0')
    visual(base,'face','visor','0 0 1.37 0 0 0','1 1 1 1','face')
    # A simulated scanner above the shell avoids self-occlusion in this model.
    visual(base,'lidar_cap',('cylinder',(.032,.014)),'0 0 1.565 0 0 0',BLACK)
    sensor=tag(base,'sensor',name='tour_lidar',type='gpu_lidar')
    tag(sensor,'pose','0 0 1.58 0 0 0')
    tag(sensor,'topic','/scan'); tag(sensor,'gz_frame_id','laser_frame')
    tag(sensor,'update_rate','8'); tag(sensor,'always_on','true')
    lidar=tag(sensor,'lidar'); scan=tag(lidar,'scan')
    horizontal=tag(scan,'horizontal')
    for key,value in [('samples',720),('resolution',1),('min_angle',-math.pi),('max_angle',math.pi)]:tag(horizontal,key,value)
    vertical=tag(scan,'vertical')
    for key,value in [('samples',1),('resolution',1),('min_angle',0),('max_angle',0)]:tag(vertical,key,value)
    ranges=tag(lidar,'range')
    for key,value in [('min',.12),('max',20),('resolution',.01)]:tag(ranges,key,value)
    visual(base,'tablet_frame',('box',('.045 .35 .52',)),'0.225 0 .94 0 -.18 0')
    visual(base,'tablet_bezel',('box',('.012 .325 .49',)),'0.253 0 .945 0 -.18 0',BLACK)
    visual(base,'tablet_display','screen','0.261 0 .946 0 -.18 0','1 1 1 1','screen')
    for side in (-1,1):
        visual(base,f'ear_{side}',('cylinder',(.097,.045)),f'0 {side*.18} 1.37 1.5707963 0 0')
        visual(base,f'ear_gold_{side}',('cylinder',(.088,.012)),f'0 {side*.209} 1.37 1.5707963 0 0',GOLD)
        visual(base,f'ear_light_{side}','ring',f'0 {side*.217} 1.37 1.5707963 0 0',GOLD,emissive='0.9 0.64 0.32 1')
        visual(base,f'shoulder_{side}',('sphere',(.075,)),f'0 {side*.215} 1.065 0 0 0')
        for name,x,y,z,radius,length,pitch in [('upper',0,.265,.965,.046,.20,-.12),('fore',.055,.258,.79,.041,.17,.57)]:
            pose=f'{x} {side*y} {z} 0 {pitch} 0'
            visual(base,f'arm_{side}_{name}',('cylinder',(radius,length)),pose)
            visual(base,f'arm_gold_{side}_{name}',('cylinder',(radius*.68,length*.88)),f'{x} {side*(y+.033)} {z} 0 {pitch} 0',GOLD)
        visual(base,f'elbow_{side}',('sphere',(.048,)),f'0.01 {side*.265} .865 0 0 0',GOLD)
        visual(base,f'hand_{side}',('sphere',(.046,)),f'.104 {side*.258} .718 0 0 0')
    # Narrow white-gold illuminated lower band, with wheels recessed underneath.
    visual(base,'bottom_gold','base_gold','0 0 .08 0 0 0',GOLD)
    visual(base,'bottom_light','base_light','0 0 .11 0 0 0',WHITE,emissive='1 .7 .4 1')
    for side,name in [(1,'left'),(-1,'right')]:
        link=tag(model,'link',name=name+'_wheel')
        tag(link,'pose',f'0 {side*.22} .085 -1.5707963 0 0')
        inertia(link,.65,0,(.0013,.0013,.00235))
        collision(link,'tire','cylinder',(.085,.045),'0 0 0 0 0 0')
        visual(link,'tire',('cylinder',(.085,.045)),color=BLACK)
        joint=tag(model,'joint',name=name+'_wheel_joint',type='revolute')
        tag(joint,'parent','base_link'); tag(joint,'child',name+'_wheel')
        axis=tag(joint,'axis'); tag(axis,'xyz','0 0 1')
        limit=tag(axis,'limit'); tag(limit,'effort','20'); tag(limit,'velocity','12')
        tag(tag(axis,'dynamics'),'damping','.01')
    drive=tag(model,'plugin',filename='gz-sim-diff-drive-system',name='gz::sim::systems::DiffDrive')
    for key,value in [('left_joint','left_wheel_joint'),('right_joint','right_wheel_joint'),('wheel_separation',.44),('wheel_radius',.085),('topic','/heritage_robot/cmd_vel'),('odom_topic','/heritage_robot/odom'),('tf_topic','/heritage_robot/tf'),('frame_id','odom'),('child_frame_id','base_link'),('odom_publish_frequency',30),('max_linear_velocity',.35),('min_linear_velocity',-.35),('max_angular_velocity',.8),('min_angular_velocity',-.8),('max_linear_acceleration',.3),('min_linear_acceleration',-.3),('max_angular_acceleration',.8),('min_angular_acceleration',-.8)]:tag(drive,key,value)
    E.indent(sdf); E.ElementTree(sdf).write(ROOT/'model.sdf',encoding='utf-8',xml_declaration=True)
    config=E.Element('model'); tag(config,'name','非遗智伴'); tag(config,'version','1.0')
    tag(config,'sdf','model.sdf',version='1.9'); tag(config,'description','Reference-inspired mobile exhibition guide; dimensions and mass estimated for simulation.')
    E.ElementTree(config).write(ROOT/'model.config',encoding='utf-8',xml_declaration=True)


if __name__ == '__main__':
    build()
    print('Built heritage_guide: height 1.55 m, base diameter 0.60 m')
