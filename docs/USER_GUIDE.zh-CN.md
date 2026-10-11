# MicroScale Editor — 简体中文使用手册

[English](USER_GUIDE.md) · [简体中文（zh-CN）](USER_GUIDE.zh-CN.md) · [项目主页](../README.md) · [Windows 下载](https://github.com/CapricciosoSZU/MicroScaleEditor/releases/latest)

适用版本：**v0.2.1**。手册更新日期：**2026-10-11**。软件界面仍为英文；本手册保留加粗的英文按钮和字段名称，方便在软件中查找。文中的数值仅用于演示，不是对你的图像进行的实际测量。

MicroScale Editor 用于制作经过物理尺寸校准的 SEM/TEM 实空间图像。原始图像数组保持只读；裁剪、旧标注处理、校准和样式分别记录。图像处理在本机完成。

## 目录

1. [快速开始](#quick-start)
2. [导入图像与认识界面](#opening-several-images)
3. [校准图像](#three-input-workflows)
4. [绘制与移动比例尺](#scale-bar-styling)
5. [裁剪与查看图像](#cropping-and-navigation)
6. [处理已有比例尺](#existing-annotations-and-masks)
7. [添加关联局部放大图](#linked-inset)
8. [测量与检查](#measure-and-review)
9. [导出展示图与科学数据](#export)
10. [保存项目与恢复工作](#projects-recovery-and-replay)
11. [键盘与鼠标快捷操作](#shortcuts)
12. [常见问题](#troubleshooting)
13. [支持范围与更多帮助](#scope-and-help)

<a id="quick-start"></a>
## 1. 快速开始

如果图像上已有清晰、完整的比例尺：

1. 点击 **Open image…**，选择图像。
2. 中间选择 **Edit • source coordinates**（源坐标编辑视图），右侧选择 **Source**。
3. 点击 **Pick endpoints**，在已有比例尺的一端按下鼠标，**拖到另一端后松开**。需要时放大图像并微调端点。
4. 对于水平比例尺，将两个端点的 **y** 值设为相同。**先放好端点，再在 Known length 中填写旧比例尺标注的长度**，例如 `50 nm`。
5. 只有在有依据认为横纵采样间距相等时，才勾选 **Assume square pixels**。点击 **Use endpoints**，检查计算出的校准值，再点击 **Confirm calibration**。
6. 打开 **Scale bar**，选择 **Preset** 并点击 **Use preset**；然后勾选 **Draw a physical scale bar**。填写新比例尺的 **Physical length**，选择 **Position**，点击 **Apply style / length**。
7. 同时检查旧标注：[保留、裁去，或按需要处理](#existing-annotations-and-masks)。添加新比例尺不会自动去掉旧比例尺。
8. 在 **Output pixel preview** 中检查结果。进入 **Export**，点击 **Export check / locate**，选择 **Format**，再点击 **Export…**。用 **Save project…** 保存可继续编辑的项目。

若图中没有可读比例尺，可使用可靠的像素物理间距、受支持的元数据，或经过验证的配对参考图校准，方法见下文。也可以通过 **File → Synthetic examples** 打开人工合成示例练习。

<a id="opening-several-images"></a>
## 2. 导入图像与认识界面

下载并运行 `MicroScaleEditor.exe`，无需单独安装 Python。标题栏显示版本号。首次显示时，窗口在鼠标所在显示器的可用区域内居中；之后手动移动窗口的位置会被尊重。

**Open image…** 支持 PNG、JPEG 和受支持的单页 TIFF，包括 LZW 压缩 TIFF。在同一个文件选择窗口中，可用 **Ctrl+单击**逐个选择、**Shift+单击**连续选择，或 **Ctrl+A** 全选。导入后在左侧图像列表点击某张图，即可编辑它。

每张图的校准和编辑状态独立。批量导入不等于批量校准或批量导出。v0.2.1 需要**逐张导出**。导入的原始数组会保留在内存中，数量较多时建议分组处理。

| 界面区域 | 用途 |
|---|---|
| 左侧图像列表 | 选择图像；打开、保存或恢复项目 |
| **Edit • source coordinates** | 放置校准端点、绘制裁剪和蒙版、移动比例尺和插图 |
| **Output pixel preview** | 检查最终合成效果；修改位置和形状需返回编辑视图 |
| **Source** | 校准、参考图匹配、旧标注、显示范围 |
| **Crop** | 裁剪形状与关联局部放大图 |
| **Scale bar** | 新比例尺的长度、外观和位置 |
| **Export** | 输出尺寸、检查、格式和复制到剪贴板 |

![MicroScale Editor 比例尺设置界面，图中使用 SYNTHETIC 人工合成示例](images/editor.png)

*界面示例使用人工合成数据，不是真实样品图像。*

右侧面板可以滚动。点击 **Old scale detection and mask tools** 等折叠栏目可展开更多功能。

**填完参数后先应用，再进行其他操作。** 很多字段需要点击对应的 **Use…** 或 **Apply…** 按钮才会生效。提交操作可能刷新尚未应用的值。现在拖动端点会保留正在填写的已知长度，但放置端点后再次检查长度仍是好习惯。先使用预设，再修改新比例尺的长度和外观。

<a id="three-input-workflows"></a>
## 3. 校准图像

校准用于确定一个原始像素代表多少实际距离。它与新绘制比例尺想表示的长度是两个不同的设置。

| 字段 | 含义 | 示例 |
|---|---|---|
| **Source → Known length** | 已有比例尺或参考线段的真实长度 | 旧比例尺标注 `50 nm` |
| **Horizontal s_x** | 水平方向每个原始像素代表的距离 | **Sample units** 选择 `nm/px`，数值填 `0.2` |
| **Vertical s_y (optional)** | 垂直方向每个原始像素代表的距离 | 有依据时填写，或明确采用方形像素假设 |
| **Scale bar → Physical length** | 希望新比例尺表示的实际长度 | 新比例尺标注 `5 nm` |

计算示例：旧比例尺为 **50 nm**，测得跨度为 **250 个原始像素**，则 `50 / 250 = 0.2 nm/px`。新绘制的 **5 nm** 比例尺在原生 1× 输出时宽 **25 像素**，在 2× 输出时宽 **50 像素**。这些数值只用于说明计算方法，不能直接套用到其他图像。

### 3.1 理解校准状态

| 状态 | 含义 |
|---|---|
| **Uncalibrated** | 尚未建立可用的像素物理间距 |
| **Pending** | 已提出校准值，等待检查与确认 |
| **Confirmed** | 你已确认当前校准依据 |

软件绘制的新比例尺为水平方向，需要**已确认的水平校准**。仅测量一根水平参考线不能确定垂直采样间距。不勾选 **Assume square pixels** 时，完全水平的线段只校准 x，垂直线段只校准 y；斜线段需要有依据的方形像素假设。

方形像素指横纵方向的物理采样间距相同，与图像外形是否为正方形无关。DPI/PPI、屏幕缩放以及显微镜的名义放大倍数（例如 `×70k`）不能在这里直接作为 nm/px 校准值。

### 3.2 方法 A：手动测量已有比例尺

1. 打开图像，选择 **Source** 和 **Edit • source coordinates**。
2. 用鼠标滚轮放大已有比例尺。
3. 点击 **Pick endpoints**，在比例尺一端按下鼠标，拖到另一端后松开。需要按住拖动，而不是分开点击两次。
4. 拖动端点微调，或填写 **Endpoint 1 · x / y** 与 **Endpoint 2 · x / y**。水平比例尺的两个 y 值应完全相同。
5. 端点设置完成后，在 **Known length** 中填写图上标注的长度和单位。只有旧比例尺确实标注 `5 nm` 时，才填 `5 nm`。
6. 根据依据决定是否勾选 **Assume square pixels**。使用水平参考线绘制水平比例尺时，可以不勾选。
7. 点击 **Use endpoints**，检查显示的像素间距及依据。
8. 点击 **Confirm calibration**，确认状态变为 **Confirmed**。

测量对象是**比例尺线段本身**，不是文字或底板的宽度。实心条使用左右外边缘；带端刻度的尺子使用对应标注跨度的两个刻度中心线。如果 `500 nm` 表示整把尺子的长度，应测量完整跨度，而不是一个刻度间隔。存在抗锯齿时，可在局部明暗差约一半的位置判断边缘。

修改端点后，校准会重新进入待确认状态。重新检查或填写 **Known length**，点击 **Use endpoints**，再确认校准。

确认校准后，端点工具自动切换为 **Pan**，避免误改端点。单纯裁剪会保留已确认的校准。**Scale bar** 标签页会实时显示校准提示；比例尺隐藏时可点击 **Review calibration** 返回 Source。修改端点后，必须先点击 **Use endpoints**，才能再次确认校准。

### 3.3 方法 B：用检测和 OCR 提供初始候选

1. 展开 **Source → Old scale detection and mask tools**。
2. 点击 **Detect + OCR**。如需限定检测范围，点击 **Detect region**，在编辑视图中拖出包含旧标注的矩形。
3. 在列表中选择候选，点击 **Use candidate**。
4. 检查并修正端点，然后检查 **Known length** 的数值和单位。最后执行 **Use endpoints → Confirm calibration**。

**Use candidate** 还会添加线条、文字和背景蒙版，供后续处理使用；它本身不会擦除旧标注。**Ignore false candidate** 用于将误检候选标为忽略。

检测优先针对水平实心条。刻度尺和不完整的比例尺需要特别检查。OCR 结果不会自动确认为校准值；漏识别或识别错误时可改用方法 A。参考标注不清晰或不完整时，不能靠猜测建立可靠长度。

### 3.4 方法 C：输入已知采样间距或检查元数据

如果已有可靠的像素物理间距：

1. 在 **Source** 中选择 **Sample units**：`nm/px` 或 `μm/px`。
2. 填写 **Horizontal s_x**；若垂直间距有独立依据，也填写 **Vertical s_y (optional)**。
3. 有依据时可勾选 **Assume square pixels**，此时垂直间距设为已填写的水平间距。
4. 点击 **Use manual calibration**，检查依据，再点击 **Confirm calibration**。

受支持的 OME-TIFF 物理尺寸和 MicroScale 采样间距元数据会作为 **Pending** 依据载入。请核实数值和来源后再确认。软件不保证识别所有仪器厂商的元数据。

若横纵间距均有独立依据，请在手动校准表单中同时填写。每次 **Use endpoints** 会替换当前轴向数值；先测水平线、再测垂直线不会自动累积成双轴校准。

### 3.5 方法 D：用配对参考图校准干净原图

适用于干净原图与带标注参考图具有相同底层图像内容的情况。文件名相似或尺寸相同，不足以证明二者匹配。

1. 先打开**干净原图**，点击 **Source → Set calibration reference…**，选择带标注参考图。
2. 点击 **Automatic content registration**，检查 **Registered reference / source overlap**。需要时勾选 **Flicker registered reference / source (pair check only)** 交替查看。
3. 自动匹配失败时，返回 **Correspondence points**。在两张图中按相同顺序，分别 **Ctrl+单击至少三组分布分散且不共线的对应位置**。点击 **Verify manual point pairs** 并检查叠加结果。**Clear points** 可清空后重新选点。
4. 只有在有依据时才勾选 **Assume square pixels in source and reference**；否则使用水平参考线段。
5. 建立参考图间距：可直接填写可靠的 **Reference s_x (nm/px)**；也可执行 **Detect reference scale + OCR → Use selected reference candidate**，检查 **Reference bar length**、**Reference p1 x / y** 与 **Reference p2 x / y**，再点击 **Compute reference calibration from endpoints**。端点坐标和长度也可手动填写。
6. 点击 **Transfer calibration as pending**。回到主窗口后检查转移的校准依据，再点击 **Confirm calibration**。

红色对应点用于验证图像匹配；黄色参考端点用于测量比例尺长度，二者用途不同。配准成功之前，转移按钮不可用。匹配支持平移和均匀缩放，包括内容对应的裁剪图或附加页脚；不可靠匹配和不支持的变换会被拒绝。参考配准不会重采样干净原图。

### 3.6 校准依据发生冲突时

软件根据 **Review threshold (%)** 比较当前值与历史依据，初始阈值为 2%。发生冲突时，确认会被阻止。请检查单位、端点、元数据以及源图/参考图是否正确。确定当前方案有依据后，勾选 **Reviewed conflict: choose current source**，再点击 **Confirm calibration**。单纯修改比例尺外观不需要重新校准。

<a id="scale-bar-styling"></a>
## 4. 绘制与移动比例尺

### 4.1 创建新比例尺

1. 确认水平校准状态为 **Confirmed**。
2. 打开 **Scale bar** 标签页。
3. 新打开的图像默认使用 **Velox-style**：白色文字和条形配黑色描边，文字在条形上方左对齐，整组位于左下角。已有项目可选择 **Preset → Velox-style → Use preset** 应用。仍可选择 **White**（白色）、**Black**（黑色）或 **White on dark plate**（深色底板上的白色）。这一步应在其他样式编辑之前完成。
4. 勾选 **Draw a physical scale bar**。
5. 在 **Physical length** 中输入新比例尺要表示的长度和单位，例如 `5 nm`、`500 nm` 或 `1 μm`。也可以通过 **Quick physical length** 或 **Suggested lengths** 选择，再检查填入的值。
6. 设置 **Position**，例如 `bottom-right`（右下角），并按需调整 **Margin (output px)**。
7. 点击 **Apply style / length**，在 **Output pixel preview** 中查看比例尺和文字。

软件会根据校准值计算条形宽度，无需手绘出像素宽度。要改变所表示的长度，修改 **Physical length** 后再次应用。要隐藏新比例尺，取消 **Draw a physical scale bar** 并应用。

**Velox-style** 参照提供的 Thermo Fisher Velox 示例外观。初始字号、条形、描边和边距随图像尺寸设置。已有项目与模板保留原样式；应用预设保留当前物理长度和校准，不会自动启用比例尺或确认校准。黑色条形边框位于校准长度的外边界以内：测量应使用完整外边缘跨度，不能只量中间白色部分。

![人工合成渐变背景上的 Velox-style 比例尺](images/velox-style.png)

### 4.2 整体移动比例尺与文字

1. 返回 **Edit • source coordinates**。
2. 在 **Scale bar** 中点击 **Drag group**，工具栏会切换为 **Move scale**。
3. 拖动比例尺组到目标位置。画布获得焦点时，方向键每次移动 1 个输出像素；**Shift+方向键**每次移动 10 个。

精确定位时，选择 **Position → custom**，填写 **Group x (output px)** 和 **Group y (output px)**，再应用。这是整个比例尺组（含文字/底板空间）的左上角坐标。拖动后会切换到自定义位置。移动不会改变物理长度。

在编辑视图双击比例尺或文字组，可修改其物理长度。整个比例尺组必须位于有效裁剪范围内；圆形或多边形外侧的角落不能用于放置标注。

### 4.3 调整外观与复用样式

| 控件 | 用途 |
|---|---|
| **Color** | 颜色名称或 `#RRGGBB`，例如白色 `#ffffff`、黑色 `#000000` |
| **Bar thickness (px)** | 在 native/width 模式中，以输出像素为单位设置条形厚度 |
| **Background plate** | 在新比例尺和文字后面添加底板 |
| **Outline bar and text** | 在文字周围及条形内部添加描边，无需矩形底板 |
| **Outline color / Outline width (px)** | 在展开的详细设置中调整描边颜色与宽度；宽度必须小于条形厚度和长度的一半 |
| **Text alignment** | 文字和条形在同一组内左对齐、居中或右对齐 |
| **Font, end ticks and background details** | 展开后设置 **End ticks**、**Font family**、**Font size (px)**、**Bold**、**Text**（`above`/`below`）、**Text gap (px)**、**Plate color**、**Plate opacity** |

修改后点击 **Apply style / length**。在 **print** 输出模式中，字号和条形厚度使用 **Export → Print font / bar (pt)**，而非像素字段。可用字体取决于本机安装情况。

打印模式下描边随条形厚度缩放。**2× / 4×** 分辨率按钮也会随布局同步缩放描边。预览、PNG、带标注 TIFF/原格式输出、剪贴板和可编辑 SVG 文字均保留描边。选择普通 White/Black 预设会关闭描边。含新描边字段的项目或模板请用 v0.2.1 或更新版本重新打开。

**Save template… / Load template…** 保存或读取比例尺样式。**Copy settings… / Paste settings** 可在已打开图像间复制选定的样式/输出设置，默认不复制校准。明确选择复制校准时，目标图的校准会变为 **Pending**，需重新检查并确认。

<a id="cropping-and-navigation"></a>
## 5. 裁剪与查看图像

1. 打开 **Crop**，在 **Shape** 中选择 `rectangle`（矩形）、`square`（正方形）、`circle`（圆形）、`ellipse`（椭圆）、`polygon`（多边形）或 `freehand`（自由绘制）。
2. 按需选择 **Aspect W:H** 宽高比；`Custom` 使用 **Custom W:H** 中的值。固定比例改变的是裁剪范围，不会拉伸样品。
3. 点击 **Draw crop**，在编辑视图绘制。矩形/椭圆类形状通过拖动绘制；多边形逐点单击后按 **Enter** 或右键闭合；自由绘制松开鼠标后闭合。
4. 在工具栏选择 **Edit crop**，移动选区或调整控制点。矩形数值范围可通过 **Source x / y**、**Width / height** 修改，再点击 **Apply geometry**。
5. 设置 **Outside shape** 为 `transparent`、`white`、`black` 或 `custom`，点击 **Apply background**。

多边形/自由绘制裁剪可拖动顶点调整，Ctrl+单击插入顶点，Delete 删除所选顶点；至少保留三个顶点且边不交叉。非矩形导出使用外接矩形，形状外部按所选背景处理。预览中的透明棋盘格不会导出。

滚轮缩放，中键拖动或 **Pan** 平移，**Fit** 适应视图，**100%** 查看像素。视图缩放不改变校准。裁剪坐标使用原始图像像素，比例尺位置使用输出像素。

<a id="image-rotation"></a>
### 旋转输出图像

1. 打开 **Crop → Image rotation**。
2. 点击 **Rotate left 90°**（左转）、**Rotate right 90°**（右转）或 **Rotate 180°**，在当前角度基础上旋转。
3. 任意角度请在 **Angle (° clockwise)** 中输入 −180 到 180 之间的数值，点击 **Apply rotation**。正数为顺时针，负数为逆时针；该字段设置总角度，不是追加旋转。
4. 软件自动打开 **Output pixel preview** 查看结果。**Reset rotation** 恢复 0°。撤销/重做、项目保存、PNG/TIFF/SVG 导出及剪贴板均保留旋转角度。

旋转作用于裁剪后的图像，新比例尺、文字和插图面板随后排版。画布会扩大以容纳完整裁剪，外侧区域使用 **Outside shape** 设置。新比例尺保持水平；锚定位置的比例尺在能容纳时会自动移入有效区域，自定义位置仍由你控制。插图内容跟随主图旋转，其比例尺独立保持水平。

**Edit • source coordinates** 始终使用原始坐标朝向，以便校准、裁剪、蒙版和 ROI 编辑；最终旋转结果请在 **Output pixel preview** 中查看。输出宽度指扩展后的旋转画布宽度。源数组和原文件保持不变。

原生 1× 的整 90° 旋转只重新排列像素，数值精确保留；任意角度会插值，数据 TIFF 也一样。导出附属文件记录角度、是否插值和源到输出的变换矩阵，有效区域蒙版标明保留范围。

90°/270° 会交换横纵采样方向。若仅校准了源图 x，旋转后水平方向未知，比例尺会隐藏。任意角度的物理比例尺及输出轴向元数据需要已确认且相等的 x/y 间距，可使用有依据的方形像素假设或独立确定的相等数值。间距不等或缺失时，仍可旋转图像，但导出展示图前需关闭物理比例尺；软件不会猜测缺失校准。

<a id="existing-annotations-and-masks"></a>
## 6. 处理已有比例尺

先用旧比例尺完成校准，再决定是否将它从成图中排除：

| 方式 | 操作与效果 |
|---|---|
| 保留 | 选择 **Treatment → keep**，点击 **Apply treatment**，保留已有像素 |
| 使用干净原图 | 按配对参考图流程，将校准转移到干净原图 |
| 裁去底部信息栏 | 点击 **Crop off selected footer**，输入页脚第一行的原始 y 坐标；从该行起向下全部排除 |
| 填充均匀标注区域 | 标记范围，选择 **solid** 和 **Opaque fill color**，检查并勾选 **Uniform annotation background confirmed**，再点击 **Apply treatment** |
| 明确覆盖 | 标记范围，选择 **plate** 和 **Opaque fill color**，点击 **Apply treatment**；对所选蒙版范围进行不透明覆盖 |

裁页脚命令会将当前裁剪替换为全图宽度、截止到指定行的矩形。若需要其他形状或宽度，请用常规裁剪工具。

在 **Source → Old scale detection and mask tools** 中，**Mask layer** 可选 `line`、`text` 或 `background`，对应蓝色、粉色、黄色叠加层。在编辑视图使用 **Rectangle**、**Polygon**、**Brush** 或 **Eraser** 标记；**Expand 1 px**、**Shrink 1 px**、**Clear layer** 作用于当前层。处理操作使用各层形成的蒙版，请同时检查旧线条与文字。

工具栏 **Masks** 只控制蒙版叠加层是否可见，不决定处理是否生效。修改用于 `solid` 处理的蒙版后，应重新检查范围、确认均匀背景，再应用处理。校准端点与处理蒙版彼此独立。

新比例尺的 **Background plate** 是样式选项，不会自动识别或移除旧标注。覆盖或纯色填充均不能恢复已被文字遮挡的样品细节。软件不提供图像修补或生成式填充。

<a id="linked-inset"></a>
## 7. 添加关联局部放大图

插图来自当前图像的数字裁剪与放大，不是另一次独立观测。

1. 在 **Crop → Linked inset · digital crop of this source** 中，按需选择 **Circular (square source ROI)**，点击 **Draw source ROI**，在编辑视图拖出原图取样区域。
2. 勾选 **Show linked inset**，检查 **ROI x / y**、**ROI width / height**、**Panel x / y (output)** 和 **Panel width (output px)**，点击 **Apply inset**。
3. 点击 **Move / resize panel**，在编辑视图移动插图，或拖动其右下角调整尺寸。**Edit source ROI** 则用于改变原图取样区域。
4. 点击 **Inset scale style…**，启用并设置插图自己的比例尺，点击对话框中的 **Apply**。检查结果与导出提示。

ROI 坐标使用原始像素；插图位置和宽度使用输出像素。圆形插图要求原图 ROI 为正方形。移动或缩放插图面板不改变它取样的原图区域。

插图取自原始图像加上已记录的处理层，不包含主图新绘制的比例尺和文字。它共用源图校准，但按自身放大比例独立计算尺长。例如：80 px 宽的源区显示为 320 px，在 `0.2 nm/px` 校准下，插图中的 `5 nm` 比例尺宽 100 px。

**Export inset…** 可单独导出插图，使用当前 **Export** 中选择的格式。

<a id="measure-and-review"></a>
## 8. 测量与检查

在工具栏选择 **Measure**、**Measure horizontal** 或 **Measure vertical**，在编辑视图拖动线段。测量使用源坐标；所需方向的物理间距未知时，结果以像素报告。**Clear measurements** 清除测量记录。

**Protect polygon** 用于标记重要样品区域。逐点点击并闭合多边形后，导出检查可提示裁剪、处理蒙版、比例尺或插图与该区域的重叠。**Clear protected regions** 清除保护区域。

画布获得焦点时按住 **B**，可在相同裁剪、输出比例和显示范围下查看原图；松开后返回。**Show changes** 也使用相同基准比较，单纯改变输出采样不会被显示为额外编辑。这些检查不能证明科学结论正确，也不保证已找出所有旧标注。

显示对比度在 **Source → Display mapping → Low / high → Apply display window** 中调整，只影响展示映射，不改变原始数据值。测量/保护辅助线默认不导出；需要时勾选 **Export → Include measurement / protected guides** 并应用。

<a id="export"></a>
## 9. 导出展示图与科学数据

### 9.1 设置尺寸、检查与保存

1. 打开 **Export**，在 **Resolution** 中点击 **2×** 或 **4×** 放大输出，点击 **1×** 恢复原生采样。这些按钮立即同步缩放图像、比例尺字号/厚度/边距与插图布局。若需指定尺寸，选择 **Mode**：`native` 使用 **Native uniform factor**；`width` 使用 **Custom width (px)**，高度按比例计算；`print` 使用 **Panel width (mm)**、**DPI** 和 **Print font / bar (pt)**。
2. 按需填写 **Panel label** 及位置，点击 **Apply output layout**。
3. 检查 **Output pixel preview**；可用 **View output at 1:1 pixels** 按像素查看。
4. 点击 **Export check / locate**。点击带定位信息的问题可查看对应位置。展示图导出前必须解决错误；警告属于提示，需自行判断处理。
5. 保留默认 **Format → Same as source (original bit depth)**，可在保留源文件类型和数据精度的同时加入新比例尺。点击 **Export…**，指定保存位置，等待 **Exported:** 提示。

改变输出尺寸时，比例尺会按物理校准重新计算。2×/4× 按钮同步缩放现有标注布局；手动填写系数或宽度时，以像素设置的样式保持不变，请重新检查字号和边距。初始采样为 1×。例如 2048 × 2048 图像在 2× 时导出 4096 × 4096，在 4× 时导出 8192 × 8192；这是对现有像素插值，不会增加样品的真实细节。导出尺寸与屏幕缩放无关；软件不提供横纵方向独立拉伸。

### 9.2 选择合适格式

| **Format** 选项 | 输出内容 |
|---|---|
| **Same as source (original bit depth)** — 默认 | 带标注的 TIFF、PNG 或 JPEG，保留源文件类型、数据类型/位深与通道数；支持 uint16 PNG/TIFF 与 float32 TIFF |
| **PNG presentation** | 按记录的显示范围映射为 8-bit RGBA，包含标注，支持透明 |
| **TIFF presentation + data** | 8-bit 展示 TIFF，以及独立的原始数据类型 `_data.tif` 和有效区域蒙版 |
| **TIFF data only** | 保留原始数据类型的裁剪，不烧入处理层或新标注；原生 1× 且仅整 90° 旋转时保留精确源数据值 |
| **SVG editable annotations** | 内嵌位图与可单独编辑的条形、端刻度、文字、插图对象；显微图像像素仍是位图 |

**Same as source** 直接从源数据渲染。原生 1× 且仅整 90° 旋转时，TIFF/PNG 中标注和处理区域之外的数值保持精确；放大或任意角度旋转会插值，但仍保留原始数据类型。显示范围用于将标注颜色映射到源数据值，不会把样品像素统一转换成显示值。其他查看器可能以不同对比度显示科学 TIFF。灰度源图保持灰度，彩色标注会转为灰度。RGBA 保留透明通道；无透明通道的输入选择 `transparent` 时，不规则裁剪外部使用白色。需要按显示映射导出 8-bit 彩色/透明成图时，选择 **PNG presentation**。TIFF 使用无损 Deflate，PNG 无损；JPEG 以质量 98 重新编码，仍有损。不会完整复制原有厂商元数据与压缩参数。

每次导出带有 JSON 附属文件，记录校准、源文件哈希、显示范围、变换与处理配方。原格式成图与数据 TIFF 还会写出 `_valid-mask.png`。数据 TIFF 的不规则裁剪仍保留外接矩形中的数据，由蒙版标明有效区域。请将这些附属文件与数据一起保存。带标注的输出会有意改变相应像素；需要不含处理层和新标注的数据时，请使用 **TIFF data only**。

非原生尺寸或任意角度旋转的数据 TIFF 会重采样，并在记录中说明。要得到精确源值裁剪，请选择 `native`、系数为 `1`，旋转角度为 90° 的整数倍。**TIFF data only** 不把可见比例尺写入数据，也不执行展示标注检查。需要带可见比例尺的成图时，应选择展示格式。

**Copy finished image** 按输出分辨率复制成图，与当前查看缩放无关，并执行展示图导出检查。软件禁止覆盖输入图像；输出重名时添加编号后缀。支持中文、其他 Unicode 字符和含空格路径。

### 9.3 不校准也能导出吗？

可以裁剪并导出未校准图像。取消主图以及任何已启用插图样式中的 **Draw a physical scale bar**，应用后再检查导出。不能将猜测的比例尺作为已确认的物理长度展示。

<a id="projects-recovery-and-replay"></a>
## 10. 保存项目与恢复工作

**Save project…** 保存校准依据、假设、裁剪、蒙版、插图、测量、样式、显示映射和输出设置。**Open project…** 可恢复。项目 JSON 引用原始图像路径，不内嵌原始像素；同目录中的关联 `.npz` 蒙版文件也需要保留。

移动项目时，应保留源图和参考图。**File → Relink source…** 可以重新指定内容相同、位置改变的源图；哈希不匹配会被拒绝。另一张图需要独立项目和校准。导出的 PNG/TIFF/SVG 自带图像内容，但其处理配方仍引用原始文件。

**Undo / Redo** 撤销或重做参数变化，不复制整个原始数组。短暂空闲后，软件将恢复项目及 `.bak` 备份写入 `%LOCALAPPDATA%\MicroScaleEditor\recovery`。点击 **Recover autosave…** 可打开恢复文件或备份。手动保存也会保留备份。

便携 EXE 的日志位于 `%LOCALAPPDATA%\MicroScaleEditor\logs\microscale.log`。从源码运行时，日志通常位于仓库的 `logs/microscale.log`。

源码用户可在独立进程中重放已保存配方：

```powershell
.\.venv\Scripts\python.exe -m microscale --recipe examples\SYNTHETIC_demo.micro.json --output replay.png --format png
```

省略 `--format` 时，现默认选择 `source`；显式指定 `--format png` 则生成 8-bit 展示图。EXE 命令行与诊断方法见 [Windows 打包说明](../PACKAGING.md)。

<a id="shortcuts"></a>
## 11. 键盘与鼠标快捷操作

| 操作 | 快捷键或鼠标动作 |
|---|---|
| 打开图像 / 打开项目 | Ctrl+O / Ctrl+Shift+O |
| 保存项目 / 另存为 | Ctrl+S / Ctrl+Shift+S |
| 导出 / 复制成图 | Ctrl+E / Ctrl+Shift+C |
| 撤销 / 重做 | Ctrl+Z / Ctrl+Y |
| 缩放 / 平移 | 滚轮 / 中键拖动，或 **Pan** |
| 适应视图 / 100% | 画布获得焦点后按 F / 1 |
| 查看原图对照 | 画布获得焦点后按住 B |
| 放置校准端点 | **Pick endpoints**，然后按下、拖动、松开 |
| 移动比例尺组 | **Drag group** 后拖动；方向键移动 1 输出像素，Shift+方向键移动 10 |
| 修改新比例尺长度 | 在编辑视图双击比例尺组 |
| 完成多边形 / 取消当前绘制 | Enter 或右键 / Esc |
| 编辑多边形顶点 | 拖动；Ctrl+单击插入；Delete 删除所选顶点 |
| 选择参考图对应点 | 在参考图对话框中 Ctrl+单击两图的匹配位置 |

画布快捷键要求画布具有焦点，在字段中输入文字时不会触发。绘制和移动对象请使用编辑视图。

<a id="troubleshooting"></a>
## 12. 常见问题

| 问题 | 检查与处理 |
|---|---|
| 新比例尺没有出现 | 查看比例尺控件上方的实时提示，点击 **Review calibration**；确认旋转后水平方向的间距；勾选 **Draw a physical scale bar**；点击 **Apply style / length**；使用对比明显的颜色并检查导出问题 |
| 校准仍是 **Pending** | 点击 **Use endpoints** 或 **Use manual calibration**，检查后再 **Confirm calibration**；如有依据冲突需先解决 |
| 提示 “An oblique segment…” | 看似水平的拖动可能导致两个 y 值不同。水平条应将 y 设为相同；仅在有依据时采用方形像素假设 |
| 已知长度或样式字段被重置 | 先完成端点拖动或预设选择，再填写参数并点击对应 **Use / Apply**，之后再进行其他操作 |
| 比例尺、文字或底板超出有效裁剪 | 将整组移入，减小物理长度或字号/底板尺寸，或调整裁剪；特别检查不规则边界 |
| 比例尺过长或过短 | 核对 `nm` 与 `μm`、端点跨度、**Known length** 与 **Physical length** 的含义，以及输出系数 |
| 旧比例尺仍然存在 | 新比例尺不会擦除原有像素；检查旧标注处理，并同时包含线条和文字 |
| 拖动没有效果 | 从 **Output pixel preview** 切回 **Edit • source coordinates**，选择正确工具，并应用尚未提交的参数 |
| 浮点或 16-bit TIFF 显示很暗、对比度低 | 检查 **Source → Display mapping**；需要保留原始值时导出数据 TIFF，不要将 8-bit 预览当作原始数据 |
| `COMPRESSION.LZW` 提示需要 `imagecodecs` | 关闭旧程序，运行当前版本 v0.2.1 EXE；源码安装可用 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` 更新运行依赖 |
| 参考图转移按钮不可用或匹配被拒绝 | 验证实际内容对应与配准，检查点对和叠加；文件名一致不能解决不支持的变形或不同视野问题 |
| 导出的 TIFF 没有可见比例尺 | **TIFF data only** 不包含标注；需要保留原精度且带比例尺的 TIFF，请使用默认 **Same as source (original bit depth)**，或选择其他展示格式 |
| 导入多张图后内存占用过高 | 分组处理；所有已导入源图保留完整数组，当前没有批量导出队列 |
| 启动窗口似乎仍在旧位置 | 检查标题栏版本，关闭旧实例后启动 v0.2.1；居中只发生在初次显示，不会在每次手动移动后重置 |

<a id="scope-and-help"></a>
## 13. 支持范围与更多帮助

- 实空间长度支持 `nm`、`μm`、`µm`、`um` 和 `Å`，不支持倒空间/FFT 单位。
- 输入支持 PNG、JPEG 和单页 TIFF。DM3/DM4、PDF、多页 TIFF 工作流以及通用厂商元数据解析不在当前版本范围内。
- 支持多图导入，不支持批量导出。
- 参考配准支持平移和均匀缩放；显著旋转、镜像、非均匀缩放、畸变、纹理不足及不同视野会被拒绝。
- 处理使用全分辨率内存。150 MP 输出上限不代表任何合成都一定能装入可用内存。
- 字体依赖本机环境；精确复现文字需要相同字体环境。
- OCR、检测端点、元数据和校准转移均需检查。导入成功不代表物理校准正确。

报告问题时，请提供版本、复现步骤、相关日志片段和可公开的示例。发布前检查文件内容：项目、附属 JSON 和日志可能包含本地路径与图像标识。

[项目介绍](../README.md) · [验证范围](../VALIDATION.md) · [构建与打包](../PACKAGING.md) · [第三方声明](../THIRD_PARTY_NOTICES.md)
