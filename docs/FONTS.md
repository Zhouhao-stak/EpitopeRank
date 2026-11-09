# 字体使用与授权说明

本文件记录 EpitopeRank 的字体来源、授权状态与打包策略，用于商用合规自查。

## 结论

**项目不分发任何字体文件，也不从网络加载字体。** 界面、报告与图表只引用
操作系统已安装的字体；打包产物里曾被包含的第三方字体均为自由授权，且已裁剪
到最小集合。不存在需要付费授权的字体。

## 逐项核实

| 位置 | 使用方式 | 授权 | 是否随产品分发 |
|---|---|---|---|
| Web 界面 `--font-sans` / `--font-mono` | `system-ui`、`-apple-system`、`Segoe UI`、`Microsoft YaHei`、Arial、Consolas 等**系统字体栈** | 由操作系统授权，调用已安装字体无需额外授权 | 否，仅字体名 |
| HTML 报告 CSS | 同上系统字体栈 | 同上 | 否 |
| PDF 报告（reportlab） | Helvetica 等 PDF 标准 14 字体，只写字体名与内置 AFM 度量 | PDF 规范标准字体，不嵌入字形 | 否 |
| 图表（matplotlib） | 默认 DejaVu Sans | DejaVu / Bitstream Vera 自由许可，允许商用与再分发 | 仅保留必需字形文件 |
| 演示视频字幕生成脚本 | 本机 `C:/Windows/Fonts/msyh.ttc` 渲染像素 | Windows 系统字体，创作输出物不视为字体再分发 | 否，脚本不进交付包 |

## 冗余字体裁剪

`packaging/EpitopeRank-Desktop-OneFile.spec` 原先通过
`collect_data_files("matplotlib")` 与 `collect_data_files("reportlab")` 把两个库
的全部字体数据打进 exe：matplotlib 101 个文件约 8.46 MB、reportlab 25 个文件
约 1.06 MB，其中绝大多数（DejaVu Serif、STIX、mathtext cm 系列、LastResortHE、
reportlab 样例 TTF/PFB）本项目从不加载。

现由 `_drop_fonts()` 保守裁剪，只移除两类确定不会被加载的文件：

1. matplotlib 的 `DejaVuSerif*` 系列（默认字体是 DejaVu Sans）；
2. reportlab 的样例轮廓字体（`.pfb` / `.ttf`），PDF 只使用标准 14 字体的
   AFM 度量。

**必须保留** DejaVu Sans、`LastResortHE-Regular.ttf`、STIX/cm 系列与全部
AFM：matplotlib 的 `font_manager.py` 硬编码按路径打开
`fonts/ttf/LastResortHE-Regular.ttf` 作为兜底字体，mathtext 也可能回退到
STIX/cm。曾尝试将其一并删除，结果 `generate_figures` 抛
`FileNotFoundError`、图表目录为空。因此裁剪后必须做「出图 + HTML/PDF 报告」
的端到端冒烟，不能只看包体积。

## 维护约定

- 新增字体时，**不要**把 `.ttf` / `.otf` / `.woff` 放进仓库或交付包；
  优先使用系统字体栈。
- 若确需自带字体，必须选用 SIL OFL 1.1 / Apache-2.0 / CC0 等允许商用的字体，
  并把许可证原文一并放入 `docs/licenses/`，同时更新本文件。
- 禁止在代码里引用微软雅黑等商业字体文件并将其复制到分发目录；
  只可按字体名调用用户系统已安装的副本。
