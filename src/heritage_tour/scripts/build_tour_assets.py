#!/usr/bin/env python3
"""Local display assets for actual Gazebo screen/expression changes."""
from pathlib import Path
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
ROBOT=ROOT.parent/'heritage_robot/scripts/build_robot.py'


def build():
    spec=importlib.util.spec_from_file_location('robot_assets',ROBOT)
    robot=importlib.util.module_from_spec(spec);spec.loader.exec_module(robot)
    folder=robot.ROOT/'materials/textures'
    folder.mkdir(parents=True,exist_ok=True)
    content=json.loads((ROOT/'config/content.json').read_text(encoding='utf-8'))
    font_path=next(p for p in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','C:/Windows/Fonts/msyh.ttc'] if Path(p).exists())
    def font(size):return ImageFont.truetype(font_path,size)
    screens=[('welcome','欢迎来到非遗展厅','请选择导览模式'),('return','导览结束 · 返回待命','感谢同行'),
             ('manual','工作人员协助','自动导览已停车'),('fault','安全暂停','请确认安全后恢复')]
    screens.extend((z['id'],z['name'],'基础介绍 · 历史背景\n工艺特点 · 文化价值') for z in content['zones'])
    for name,title,subtitle in screens:
        im=Image.new('RGB',(900,1300),'#132d34');d=ImageDraw.Draw(im)
        d.rounded_rectangle((24,24,876,1276),radius=38,outline='#c6a16d',width=5)
        d.text((450,145),'非遗智伴',font=font(55),anchor='mm',fill='#dec59c')
        d.text((450,360),title,font=font(48),anchor='mm',fill='#fff5e2')
        d.multiline_text((450,580),subtitle,font=font(33),anchor='mm',align='center',fill='#e4d5bb',spacing=24)
        d.text((450,930),'传承文化 · 安全同行',font=font(35),anchor='mm',fill='#c6a16d')
        d.text((450,1150),'离线仿真演示',font=font(27),anchor='mm',fill='#a9babb')
        im.save(folder/f'tour_{name}.png')
    for expression in ('happy','waiting','alert','thinking'):
        im=Image.new('RGB',(768,768),'#02070d');d=ImageDraw.Draw(im)
        color='#d9f5ff' if expression!='alert' else '#ffbd9f'
        for x in (235,533):
            if expression=='happy':d.arc((x-62,260,x+62,425),185,355,fill=color,width=14)
            elif expression=='waiting':d.line((x-55,340,x+55,340),fill=color,width=12)
            else:d.ellipse((x-25,285,x+25,375),outline=color,width=10)
        if expression=='happy':d.arc((304,369,464,515),12,168,fill=color,width=12)
        elif expression=='alert':d.ellipse((350,440,418,504),outline=color,width=10)
        else:d.line((335,465,433,465),fill=color,width=10)
        im.save(folder/f'tour_face_{expression}.png')
    robot.mesh('tour_display',[(-1.5,0,-.8),(1.5,0,-.8),(1.5,0,.8),(-1.5,0,.8)],
               [(0,-1,0)]*4,[(0,0),(1,0),(1,1),(0,1)],[(0,1,2),(0,2,3)])
    print('Generated linked robot screen, face, and hall display assets')


if __name__=='__main__':build()
