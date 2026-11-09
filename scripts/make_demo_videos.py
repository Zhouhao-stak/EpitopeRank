"""Render two screen-style EpitopeRank demo videos from verified UI workflow copy.

The B video is explicitly marked as a concept demonstration. All example rows
are illustrative UI content, not scientific results.
"""
from pathlib import Path
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out' / 'demo_videos'
OUT.mkdir(parents=True, exist_ok=True)
# 字体合规说明：演示视频在本机调用 Windows 系统自带字体渲染字幕，
# 只生成画面像素，不复制、不嵌入、不随产品分发任何字体文件。
# 系统未安装该字体时应回退到默认字体，不得另行打包商业字体。
FONT = 'C:/Windows/Fonts/msyh.ttc'
W, H = 1280, 720
BG = '#f5f7fb'; NAV = '#101b2f'; WHITE = '#ffffff'; INK = '#152238'
MUTED = '#66768d'; BLUE = '#3478f6'; TEAL = '#12a79a'; LINE = '#e3e9f1'

def ft(n, bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else FONT, n)

def rounded(d, box, fill, radius=14, outline=None):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)

def text(d, xy, s, n=20, color=INK, bold=False):
    d.text(xy, s, font=ft(n, bold), fill=color)

def base(section, concept=False, sec=0):
    im = Image.new('RGB', (W,H), BG); d=ImageDraw.Draw(im)
    d.rectangle((0,0,222,H), fill=NAV)
    text(d,(28,26),'◈  EpitopeRank',24,WHITE,True)
    text(d,(29,65),'AI Splicing Analysis',12,'#92a6c1')
    items=['仪表盘','智能接入','AI 流水线','事件浏览器','可视化','报告','剪接候选新抗原']
    for i,item in enumerate(items):
        y=126+i*58
        if item==section: rounded(d,(12,y-8,208,y+40),'#243957',9)
        text(d,(30,y),item,17,WHITE if item==section else '#a7b8cf',item==section)
    d.rectangle((222,0,W,72), fill=WHITE)
    text(d,(252,22),'EpitopeRank  /  '+section,19,INK,True)
    rounded(d,(1050,20,1245,52),'#eaf0fa',18)
    text(d,(1071,28),'DEMO  ·  2026',13,MUTED)
    if concept:
        rounded(d,(244,86,1246,120),'#fff2df',8)
        text(d,(258,92),'概念演示  ·  以下界面为未来功能示意，示例内容不代表真实分析结果',14,'#8f5c11',True)
    else:
        rounded(d,(244,86,1246,120),'#e9f6f4',8)
        text(d,(258,92),'当前版本工作流  ·  基于现有功能制作的界面演示；示例数据仅用于说明操作',14,'#137d74',True)
    # restrained recording indicator and timeline
    d.ellipse((1174,669,1183,678),fill='#e85b64')
    text(d,(1190,663),'REC',12,MUTED,True)
    d.rectangle((244,691,1246,695), fill=LINE)
    d.rectangle((244,691,244+int(1002*sec),695), fill=BLUE)
    return im,d

def card(d, box, title, sub=None):
    rounded(d,box,WHITE,14,LINE)
    text(d,(box[0]+20,box[1]+16),title,19,INK,True)
    if sub: text(d,(box[0]+20,box[1]+48),sub,13,MUTED)

def pill(d,x,y,label,fill='#e8f0ff',fg=BLUE):
    w=max(70, len(label)*16+24)
    rounded(d,(x,y,x+w,y+29),fill,14)
    text(d,(x+12,y+5),label,13,fg,True)

def rows(d, x,y, widths, data, rowh=47):
    xx=x
    for w,h in zip(widths,data[0]):
        text(d,(xx+10,y),h,13,MUTED,True); xx+=w
    d.line((x,y+30,x+sum(widths),y+30),fill=LINE,width=2)
    for j,row in enumerate(data[1:]):
        yy=y+45+j*rowh; xx=x
        for w,value in zip(widths,row):
            text(d,(xx+10,yy),value,14,INK); xx+=w
        d.line((x,yy+rowh-12,x+sum(widths),yy+rowh-12),fill=LINE)

def draw_scene(kind, scene, t, duration):
    concept=kind=='B'; section=scene['section']; im,d=base(section,concept,t/duration)
    title=scene['title']; sub=scene['sub']
    text(d,(252,141),title,27,INK,True); text(d,(253,184),sub,15,MUTED)
    mode=scene['mode']
    if mode=='overview':
        for i,(k,v) in enumerate([('输入','rMATS JC 表'),('编排','BioPlanner → BioAnalyst → BioInterpreter'),('输出','候选事件 · 图表 · 报告')]):
            x=250+i*335; card(d,(x,235,x+315,382),k); text(d,(x+20,303),v,15,BLUE,True)
        card(d,(250,402,1238,637),'从数据到解释的可追溯分析')
        text(d,(276,466),'上传真实剪接结果  →  核对样本与字段  →  Agent 分析  →  浏览证据与报告',18,INK)
        pill(d,276,538,'目标驱动');pill(d,402,538,'质量检查');pill(d,528,538,'决策轨迹')
    elif mode=='ingest':
        card(d,(250,230,1238,635),'智能接入 · 文件识别','代表性输入：rMATS SE.MATS.JC.txt 与 sample_metadata.tsv')
        rows(d,275,308,[360,280,290],[['文件','类型','状态'],['SE.MATS.JC.txt','剪接事件 / SE','格式已识别'],['sample_metadata.tsv','样本分组','待核对'],['A3SS.MATS.JC.txt','剪接事件 / A3SS','格式已识别']])
        pill(d,278,559,'下一步：核对字段与分组')
    elif mode=='groups':
        card(d,(250,230,1238,635),'样本分组确认','逐样本核对实验组，避免根据文件名猜测真实分组')
        rows(d,275,308,[330,330,270],[['样本 ID','分组','检查'],['control_01','Control','已确认'],['control_02','Control','已确认'],['treated_01','Treated','已确认'],['treated_02','Treated','已确认']])
        pill(d,278,566,'确认分组',BLUE,WHITE)
    elif mode=='agent':
        card(d,(250,230,1238,635),'AI 流水线 · 可追溯决策','以下为流程示意；具体决策由输入数据与运行配置决定')
        steps=[('01','检查数据完整性'),('02','评估 FDR / |ΔPSI| 阈值'),('03','筛选与质控'),('04','候选排序及解释')]
        for i,(num,lab) in enumerate(steps):
            x=275+i*239; rounded(d,(x,330,x+217,441),'#f0f5fc',10);text(d,(x+17,349),num,24,BLUE,True);text(d,(x+17,394),lab,15,INK,True)
        text(d,(278,513),'决策轨迹记录每一步的输入、动作与依据；失败时可反思和重规划。',16,MUTED)
    elif mode=='events':
        card(d,(250,230,1238,635),'事件浏览器','查看 event_id、基因、事件类型、ΔPSI 与 FDR；数值仅为界面示意')
        rows(d,271,307,[240,200,130,160,170],[['Event ID','Gene','Type','ΔPSI','FDR'],['SE_demo_001','GENE_A','SE','+0.18','0.012'],['A3SS_demo_002','GENE_B','A3SS','−0.14','0.031'],['MXE_demo_003','GENE_C','MXE','+0.11','0.048']])
        pill(d,278,562,'筛选：FDR < 0.05')
    elif mode=='report':
        card(d,(250,230,710,635),'分析图表');card(d,(730,230,1238,635),'报告与结论')
        d.line((300,555,653,555),fill=MUTED,width=2);d.line((472,314,472,555),fill=MUTED,width=2)
        for i in range(65):
            xx=300+(i*37%345); yy=535-int((i*53%210)); r=3+(i%3)
            d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=TEAL if xx>470 else BLUE)
        text(d,(315,578),'ΔPSI vs −log10(FDR) 示意',13,MUTED)
        for i,s in enumerate(['数据质量与统计口径','候选事件及证据','限制与后续验证建议']):
            pill(d,760,321+i*75,s,'#edf3fb',INK)
    elif mode=='identify':
        card(d,(250,230,1238,635),'01 识别可变剪接事件','概念流程：从事件表或测序结果定位异常剪接连接')
        d.line((340,400,1120,400),fill=BLUE,width=8)
        for x,w in [(370,125),(610,125),(875,125)]: rounded(d,(x,364,x+w,436),'#dceafe',8,BLUE)
        d.arc((495,320,875,481),180,350,fill=TEAL,width=5)
        pill(d,303,521,'SE / A3SS / A5SS / MXE / RI')
    elif mode=='peptide':
        card(d,(250,230,1238,635),'02 提取新的氨基酸序列','概念流程：按已知读码框重建转录本并翻译剪接连接附近序列')
        rows(d,275,316,[300,300,320],[['阶段','输入','输出'],['剪接事件','事件坐标 + 转录本','新剪接连接'],['阅读框验证','编码序列对照','候选肽段'],['序列比对','参考蛋白组','新颖性标记']])
        text(d,(281,550),'示意肽段：M · A · L · P · E · P · T · I · D · E  （非真实患者序列）',17,TEAL,True)
    elif mode=='predict':
        card(d,(250,230,1238,635),'03 候选新抗原优先级','概念流程：结合 MHC 结合预测等证据，排序待验证候选')
        rows(d,275,312,[275,260,190,215],[['候选肽段','HLA 类型','结合预测','处理建议'],['PEPTIDE_DEMO_01','HLA-A*02:01','较强','优先验证'],['PEPTIDE_DEMO_02','HLA-B*07:02','中等','补充验证'],['PEPTIDE_DEMO_03','HLA-A*02:01','较弱','保留记录']])
        rounded(d,(278,552,1198,601),'#fff2df',8)
        text(d,(295,565),'MHC 结合预测不能证明免疫原性；仍需表达、呈递与实验验证。',16,'#8f5c11',True)
    # subtle mouse pointer movement
    cx=1040+int(12*math.sin(t*.7));cy=565+int(9*math.cos(t*.9))
    d.polygon([(cx,cy),(cx,cy+25),(cx+7,cy+19),(cx+12,cy+31),(cx+16,cy+29),(cx+11,cy+17),(cx+22,cy+17)],fill=WHITE,outline=INK)
    return im

A=[
 dict(section='仪表盘',title='EpitopeRank｜当前版本演示',sub='真实核心能力 · 从可变剪接数据到可追溯分析',mode='overview'),
 dict(section='智能接入',title='上传并识别剪接结果',sub='支持常见事件结果格式，先识别输入，再确认字段',mode='ingest'),
 dict(section='智能接入',title='人工确认样本分组',sub='保留真实实验设计，杜绝自动猜测造成的分组错误',mode='groups'),
 dict(section='AI 流水线',title='Agent 规划、分析与解释',sub='质量检查、阈值决策、筛选和解释形成完整轨迹',mode='agent'),
 dict(section='事件浏览器',title='浏览候选剪接事件',sub='结合事件类型、效应大小和统计证据检查候选',mode='events'),
 dict(section='报告',title='导出可复核的结果',sub='图表、候选排序与限制说明统一进入报告',mode='report'),
]
B=[
 dict(section='剪接候选新抗原',title='未来能力｜可变剪接与新抗原',sub='三步概念演示：事件识别 → 新肽段提取 → 候选优先级',mode='identify'),
 dict(section='剪接候选新抗原',title='从剪接变化定位新连接',sub='区分常见事件类型，为序列重建提供位置依据',mode='identify'),
 dict(section='剪接候选新抗原',title='重建并提取候选新肽段',sub='读取读码框、翻译序列、标记相对参考蛋白的新颖片段',mode='peptide'),
 dict(section='剪接候选新抗原',title='预测并排序待验证候选',sub='结合 HLA 与 MHC 结合等计算证据，形成实验验证清单',mode='predict'),
]

def render(name, scenes, seconds):
    frames=OUT/(name+'_frames');frames.mkdir(exist_ok=True)
    fps=2; total=seconds*fps
    for i in range(total):
        index=min(len(scenes)-1,i*len(scenes)//total)
        im=draw_scene(name,scenes[index],i/fps,seconds)
        im.save(frames/f'{i:04d}.png',optimize=True)
    cmd=['ffmpeg','-y','-loglevel','error','-framerate',str(fps),'-i',str(frames/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r','24','-vf','scale=1280:720',str(OUT/f'EpitopeRank_demo_{name}.mp4')]
    subprocess.run(cmd,check=True)
    print(OUT/f'EpitopeRank_demo_{name}.mp4')

if __name__=='__main__':
    render('A',A,90)
    render('B',B,60)
