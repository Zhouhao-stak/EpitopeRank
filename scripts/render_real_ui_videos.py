"""Render actual SpliceGAIP browser captures into two short screen demos."""
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out'/'demo_videos'; SC=OUT/'real_screens'
FONT='C:/Windows/Fonts/msyh.ttc'; BOLD='C:/Windows/Fonts/msyhbd.ttc'

def frame(src,title,detail,progress,concept=False,wiggle=0):
    im=Image.open(SC/src).convert('RGB').resize((1440,900))
    d=ImageDraw.Draw(im,'RGBA')
    d.rounded_rectangle((283,753,1390,872),radius=16,fill=(4,15,26,235),outline=(67,216,197,170),width=2)
    d.text((307,767),title,font=ImageFont.truetype(BOLD,25),fill='#f7ffff')
    d.text((307,812),detail,font=ImageFont.truetype(FONT,16),fill='#a9c7cf')
    if concept:
        d.rounded_rectangle((1201,765,1365,798),radius=13,fill=(255,180,63,245))
        d.text((1221,771),'概念演示',font=ImageFont.truetype(BOLD,17),fill='#2e2008')
    d.rectangle((283,886,1390,890),fill='#315261')
    d.rectangle((283,886,283+int(1107*progress),890),fill='#42ddc8')
    return im

A=[
 ('01b_demo_project.png','当前项目总览','实际运行界面 · demo_rmats 示例项目'),
 ('09_new_analysis.png','创建新的剪接分析','填写项目名称、分析目标并上传真实输入文件'),
 ('02_pipeline.png','Agent 工作流','规划、分析、解释等步骤在同一页面追踪'),
 ('03_explorer.png','事件浏览器','按事件类型、FDR 与 ΔPSI 查看真实示例项目记录'),
 ('04b_volcano.png','可视化结果','项目内火山图：ΔPSI 与统计证据一起呈现'),
 ('05_gene.png','基因浏览器','定位基因并查看相关解释入口'),
 ('06_report.png','报告页面','汇总结果、导出分析报告'),
 ('07_assistant.png','AI 助手','在真实界面里继续询问候选事件与生物学解释'),
]
B=[
 ('08_neoantigen.png','01 识别可变剪接事件','基于剪接事件表确定异常连接与候选来源'),
 ('08b_neoantigen_lower.png','02 提取新氨基酸序列','提供已定读码框的编码序列对照，生成候选肽段'),
 ('08b_neoantigen_lower.png','03 候选新抗原预测','输入 HLA 类型并结合 MHC 结合证据，筛选待验证候选'),
]

def render(name,scenes,seconds):
    folder=OUT/f'real_{name}_frames';folder.mkdir(exist_ok=True)
    fps=2;n=seconds*fps
    for i in range(n):
        src,title,detail=scenes[min(len(scenes)-1,i*len(scenes)//n)]
        im=frame(src,title,detail,i/n,name=='B')
        im.save(folder/f'{i:04d}.png',optimize=True)
    target=OUT/f'SpliceGAIP_real_UI_demo_{name}.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(fps),'-i',str(folder/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r','24',str(target)],check=True)
    print(target)

if __name__=='__main__':
    render('A',A,90)
    render('B',B,60)
