import datetime
import matplotlib
import numpy as np
import os
import time
import traceback
from PIL import ImageDraw, ImageFont, Image

matplotlib.use('Agg')

import matplotlib.pyplot as plt


class ColorMap():

    def __init__(self, dataNum, colorSet='Paired'):
        self.dataNum = dataNum
        # https://zhuanlan.zhihu.com/p/158871093 颜色组预览，这里用Paired
        try:
            self.colorMap = matplotlib.colormaps.get_cmap(colorSet)
        except:
            self.colorMap = plt.cm.get_cmap(colorSet)

    def __call__(self, key):
        return self.colorMap(key / self.dataNum)

    def getColor(self, ):
        return np.arange(self.dataNum) / self.dataNum


class RadarDisplay():
    def __init__(self, radarCanvasW=400, radarCanvasH=600, worldW=40, worldH=255, worldUnitW=10, worldUnitH=20,
                 defences=None, template_png_path=os.path.join(".", "config", "radarPicTemplate.png")):
        # imgW:图像宽度，单位px
        # imgH:图像高度，单位px
        # self.worldW:图像对应现实世界的宽度，单位m
        # self.worldH:图像对应现实世界的长度，单位m
        # self.worldUnitW:图像单元格对应现实世界的宽度，单位m
        # self.worldUnitH:图像单元格对应现实世界的长度，单位m
        # self.defences
        self.using_pillow = True
        self.template_png_path = template_png_path
        self.radarCanvasW = radarCanvasW
        self.radarCanvasH = radarCanvasH
        self.worldW = worldW
        self.worldH = worldH
        self.worldUnitW = worldUnitW
        self.worldUnitH = worldUnitH
        self.defences = defences
        self.template = None
        self.createRadarCanvas()

    def createRadarCanvas(self, ):
        from PIL import Image
        dpi = 100
        # 像素与磅数互转
        # 1英寸=72磅=dpi个像素
        self.ptToPx = lambda pt: pt / 72 * dpi  # 磅数(字体高度) * 英寸/磅 * dpi(px/英寸)
        self.pxToPt = lambda px: px / dpi * 72  # px / dpi(px/英寸) * 磅/英寸
        # 磅数与fig百分比互转
        self.ptToFigRatioW = lambda pt: pt / (72 * self.radarCanvasW / dpi)  # 磅数 / 总磅数
        self.ptToFigRatioH = lambda pt: pt / (72 * self.radarCanvasH / dpi)  # 磅数 / 总磅数

        # 最大化RadarCanvas在fig中的占比
        hCharNum = 6  # 水平方向字符数，5字符加1字符留白，用于y轴坐标刻度值
        vCharNum = 3  # 垂直方向字符数，2字符加1字符留白，用于x轴坐标刻度值
        ratio = 0.4
        charWidthDivHeight = 0.60
        # 因为主图和fig比例一致，所以主图最大比例maxRatio为 1 - 2*其余元素(如坐标系)占比最大的方向的占比。可以理解为
        # 绘制(self.radarCanvasW, self.radarCanvasH)这么大的图，最后加入各种如坐标系后的元素后扩张大小后再缩放为(self.radarCanvasW, self.radarCanvasH)这么大的图
        # maxRatio = 1-2*max(ptToFigRatioW(hCharNum * fontWidthPt), ptToFigRatioH(vCharNum * fontHeightPt))
        # 主图占画布的比例*画布长度的一半 /写6组数据/每组数据占3行(2行是数据1行是间距)=字体大小 px
        # pxToPt(maxRatio * radarCanvasH *0.5 / (6 * 3)) = fontHeightPt
        # 其中consolas字体宽高比约为 charWidthDivHeight
        # fontWidthPt = fontHeightPt * charWidthDivHeight
        # 解得主图最大比例为：
        if self.ptToFigRatioW(hCharNum * charWidthDivHeight) > self.ptToFigRatioH(vCharNum):  # 如果x轴占比比较多
            # maxRatio = 1 - 2 * ptToFigRatioW(charWidthDivHeight * hCharNum * pxToPt(maxRatio * radarCanvasH *0.5 / (6 * 3))) 1 - x轴方向的其他占比
            # maxRatio = 1 - 2 * ptToFigRatioW(charWidthDivHeight * hCharNum * maxRatio * radarCanvasH *0.5 / (6 * 3) / dpi * 72)
            # maxRatio = 1 - 2 * (charWidthDivHeight * hCharNum * maxRatio * radarCanvasH *0.5 / (6 * 3) / dpi * 72) / (72 * self.radarCanvasW / dpi)
            # maxRatio = 1 - maxRatio* 2 * (charWidthDivHeight * hCharNum * radarCanvasH *0.5 / (6 * 3) / dpi * 72) / (72 * self.radarCanvasW / dpi)
            radarCanvasRatio = 1 / (
                    1 + 2 * (charWidthDivHeight * hCharNum * self.radarCanvasH * ratio / (6 * 3) / dpi * 72) / (
                    72 * self.radarCanvasW / dpi))
        else:
            # maxRatio = 1 - 2 * ptToFigRatioH(vCharNum * pxToPt(maxRatio * radarCanvasH *0.5 / (6 * 3))) 1 - y轴方向的其他占比
            # maxRatio = 1 - 2 * ptToFigRatioH(vCharNum * maxRatio * radarCanvasH *0.5 / (6 * 3) / dpi * 72)
            # maxRatio = 1 - 2 * (vCharNum * maxRatio * radarCanvasH *0.5 / (6 * 3) / dpi * 72) / (72 * self.radarCanvasH / dpi)
            # maxRatio = 1 - maxRatio* 2 * (vCharNum * radarCanvasH *0.5 / (6 * 3) / dpi * 72) / (72 * self.radarCanvasH / dpi)
            radarCanvasRatio = 1 / (1 + 2 * (vCharNum * self.radarCanvasH * ratio / (6 * 3) / dpi * 72) / (
                    72 * self.radarCanvasH / dpi))
        # 主图占画布的比例*画布长度的一半 /写6组数据/每组数据占3行(2行是数据1行是间距)=字体大小
        self.fontHeightPt = self.pxToPt(radarCanvasRatio * self.radarCanvasH * ratio / (6 * 3))
        self.fontWidthPt = self.fontHeightPt * charWidthDivHeight  # consolas字体宽高比月为 charWidthDivHeight

        fig = plt.figure("RadarDisplay", figsize=(self.radarCanvasW / dpi, self.radarCanvasH / dpi), dpi=dpi)
        self.radarCanvasAx = fig.add_axes(
            [(1 - radarCanvasRatio) / 2, (1 - radarCanvasRatio) / 2, radarCanvasRatio, radarCanvasRatio])  # 设置axes，居中对其

        # 扩展绘制
        fig = self.radarCanvasAx.figure
        dpi = self.radarCanvasAx.figure.dpi
        # 最多多26个字符宽度+1字符留白 - 右侧本来有的6
        charNum = 18
        fig.set_size_inches(self.radarCanvasW / dpi + self.ptToPx(charNum * self.fontWidthPt) / dpi,
                            self.radarCanvasH / dpi)
        originPos = self.radarCanvasAx.get_position()
        # 原大小/现在大小
        cofW = ((self.radarCanvasW) / (self.radarCanvasW + self.ptToPx(charNum * self.fontWidthPt)))
        self.radarCanvasAx.set_position(
            [originPos.x0 * cofW, originPos.y0, originPos.width * cofW, originPos.height])  # 设置axes
        # 获取图像应画单元格数
        unitNumX = self.worldW // self.worldUnitW + 1  # 完整单元格 + 1 以保证完全显示
        unitNumY = self.worldH // self.worldUnitH + 1  # 完整单元格 + 1 以保证完全显示
        # 因为需要中心线，列格需要偶数个单元格
        if unitNumX % 2 != 0:
            unitNumX -= 1
        # 获取线条数
        lineNumX = unitNumX + 1  # 线条数应在单元格的数量上加上1
        lineNumY = unitNumY + 1  # 线条数应在单元格的数量上加上1
        # 获取图像网格线坐标
        imgGridX = np.linspace(0, self.radarCanvasW - 1, lineNumX, endpoint=True).astype(np.int64)
        imgGridY = np.linspace(0, self.radarCanvasH - 1, lineNumY, endpoint=True).astype(np.int64)
        # 获取现实网格线坐标
        worldGridX = np.arange(lineNumX) * self.worldUnitW
        worldGridX = worldGridX - worldGridX[unitNumX // 2]  # 偏移x轴中心点至图像中心
        worldGridY = np.arange(lineNumY) * self.worldUnitH
        for idx, x in enumerate(imgGridX):
            if idx == unitNumX // 2:
                self.radarCanvasAx.axvline(x=x, color='black', linestyle='-', lw=self.fontHeightPt / 10)
            else:
                self.radarCanvasAx.axvline(x=x, color='black', linestyle='--', lw=self.fontHeightPt / 10)
        for idx, y in enumerate(imgGridY):
            if idx == 0:
                self.radarCanvasAx.axhline(y=y, color='black', linestyle='-', lw=self.fontHeightPt / 10)
            else:
                self.radarCanvasAx.axhline(y=y, color='black', linestyle='--', lw=self.fontHeightPt / 10)

        deviceInRadarCanvasCenter = (self.radarCanvasW / 2, 0)  # 设备在图中的位置
        # 现实世界坐标转到radarCanvasMain图片坐标的系数,单位：px/m
        worldToRadarCanvasCofX = self.radarCanvasW / unitNumX / self.worldUnitW
        worldToRadarCanvasCofY = self.radarCanvasH / unitNumY / self.worldUnitH

        self.worldToImageCofX = lambda x: (x * worldToRadarCanvasCofX + deviceInRadarCanvasCenter[0])
        self.worldToImageCofY = lambda y: (y * worldToRadarCanvasCofY)
        self.imageToWorldCofX = lambda x: (x - deviceInRadarCanvasCenter[0]) / worldToRadarCanvasCofX
        self.imageToWorldCofY = lambda y: y / worldToRadarCanvasCofY

        # 绘制坐标轴
        self.radarCanvasAx.invert_yaxis()  # 倒转y轴
        self.radarCanvasAx.set_xlim(0, self.worldW)  # 限制轴自动缩放
        self.radarCanvasAx.set_ylim(0, self.worldH)  # 限制轴自动缩放
        self.radarCanvasAx.set_xlabel('X', fontname='consolas', fontsize=self.fontHeightPt)  # 设置坐标轴标签
        self.radarCanvasAx.set_ylabel('Y', fontname='consolas', rotation=np.pi / 2,
                                      fontsize=self.fontHeightPt)  # 设置坐标轴标签
        self.radarCanvasAx.xaxis.set_label_coords(1 + self.ptToFigRatioW(self.fontWidthPt),
                                                  self.ptToFigRatioH(self.fontHeightPt))
        self.radarCanvasAx.yaxis.set_label_coords(0, 1)
        # 设置坐标轴字体大小与距离
        self.radarCanvasAx.tick_params(axis='x', labelsize=self.fontHeightPt, which='both', pad=self.fontHeightPt)
        self.radarCanvasAx.tick_params(axis='y', labelsize=self.fontHeightPt, which='both', pad=self.fontHeightPt)
        self.radarCanvasAx.set_xticks(imgGridX)  # 添加原始图像坐标系刻度
        self.radarCanvasAx.set_yticks(imgGridY)  # 添加原始图像坐标系刻度
        self.radarCanvasAx.set_xticklabels(worldGridX, fontname='consolas')  # 加添加的原始图像坐标系轴刻度映射为世界坐标系
        self.radarCanvasAx.set_yticklabels(worldGridY, fontname='consolas')  # 加添加的原始图像坐标系轴刻度映射为世界坐标系
        self.radarCanvasAx.spines['top'].set_linewidth(self.fontHeightPt / 10)  # 顶部边框宽度
        self.radarCanvasAx.spines['bottom'].set_linewidth(self.fontHeightPt / 10)  # 底部边框宽度
        self.radarCanvasAx.spines['left'].set_linewidth(self.fontHeightPt / 10)  # 左边边框宽度
        self.radarCanvasAx.spines['right'].set_linewidth(self.fontHeightPt / 10)  # 右边边框宽度
        if self.defences is not None:
            self.defences = [np.array(d) for d in self.defences]  # 复制
            colorMap = ColorMap(len(self.defences))
            for idx, d in enumerate(self.defences):
                # 约束图中防区范围
                d[:, 0][d[:, 0] < -0.5 * self.worldW] = -0.5 * self.worldW
                d[:, 0][d[:, 0] > 0.5 * self.worldW] = 0.5 * self.worldW
                d[:, 1][d[:, 1] < 0] = 0
                d[:, 1][d[:, 1] > self.worldH] = self.worldH
                clossDefence = np.concatenate([d, d[0:1]], axis=0)
                self.radarCanvasAx.plot(self.worldToImageCofX(clossDefence[:, 0]),
                                        self.worldToImageCofY(clossDefence[:, 1]), lw=self.fontHeightPt / 8,
                                        c=colorMap(idx))

        xInche, yInche = self.radarCanvasAx.figure.get_size_inches()
        # 左上角 x,y 右下角 x y
        self.radarCanvasAxLocate = (originPos.x0 * cofW * xInche * dpi, originPos.y0 * yInche * dpi,
                                    (originPos.x0 + originPos.width) * cofW * xInche * dpi,
                                    (originPos.y0 + originPos.height) * yInche * dpi)

        # 以下用于pillow库
        # 左上角 x,y 右下角 x y

        # 保存后雷达图与matplotlib雷达图的比例
        self.scaleInTemplate = ((originPos.width * cofW * xInche * dpi) / self.radarCanvasW,
                                (originPos.height * yInche * dpi) / self.radarCanvasH)

        self.pilWorldToImageCofX = lambda x: self.worldToImageCofX(x) * self.scaleInTemplate[0] + \
                                             self.radarCanvasAxLocate[0]
        self.pilWorldToImageCofY = lambda y: (self.radarCanvasH - self.worldToImageCofY(y)) * self.scaleInTemplate[1] + \
                                             self.radarCanvasAxLocate[1]
        self.pilImageToWorldCofX = lambda x: self.imageToWorldCofX(
            (x - self.radarCanvasAxLocate[0]) / self.scaleInTemplate[0])
        self.pilImageToWorldCofY = lambda y: self.imageToWorldCofY(
            self.radarCanvasH - ((y - self.radarCanvasAxLocate[1]) / self.scaleInTemplate[1]))

        print(f"{datetime.datetime.now()} createRadarCanvas template_png_path={self.template_png_path}")
        self.radarCanvasAx.figure.savefig(self.template_png_path)
        self.template = Image.open(self.template_png_path)
        self.template =self.template.convert("RGB")
        self.template.save(self.template_png_path)

    def surePos(self, objPos, blockPos, textBlockW, textBlockH):  # 防止注释重叠
        # 后续开发问题：1.未解决目标过多绘制区域分配问题。2.注释文本默认字数是保持递增的，如果不是应该对文本块采用iou计算，例如前
        # 前一个注释为xxxxxxx，后一个注释为x，可能就会相互重叠
        # 因为annotate函数中不知道其注释文本的起始坐标, 将文本大小放大2倍，确保不管文本的起始坐标
        # 在左下角还是哪个位置，都能被宽高为textBlockW，textBlockH的块围住，这个块即注释占有区域
        textBlockW = textBlockW * 2
        textBlockH = textBlockH * 2
        lengthInterval = np.linalg.norm([textBlockW, textBlockH])  # 每次长度加值，文本块对角线长度

        relatePos = 2 * np.array([self.ptToPx(self.fontHeightPt), self.ptToPx(self.fontHeightPt)])  # 文本块中心距离目标点初始相对位置
        nowAngle = 0  # 当前文本块中心与目标点连线的角度
        nowLenth = np.linalg.norm(relatePos)  # 当前文本块中心与目标点连线的距离
        nowAbsPos = relatePos + objPos  # 当前文本块在目标点所在坐标系下的位置
        while True:
            goodPos = True  # 判断是不是好的文本位置
            for block in blockPos:  # 循环判断新的注释区域与已有注释区域是否存在重叠
                x, y = nowAbsPos
                # 应该距离图像边缘一定距离
                flag1 = (x > textBlockW) & (x < self.radarCanvasW - textBlockW) & (y > textBlockH) & (
                        y < self.radarCanvasH - textBlockH)
                # 应该与已有文本块存在一定距离
                dis = np.abs(block - nowAbsPos)
                flag2 = (dis[0] > textBlockW) or (dis[1] > textBlockH)
                if not flag1 or not flag2:
                    goodPos = False
                    break
            if goodPos:
                return nowAbsPos

            angleInterval = max(textBlockW, textBlockH) / nowLenth  # 每次角度加值(rad)，转的弧长要大于文本框宽高的最大值
            nowAngle += angleInterval  # 更新当前注释角度
            if nowAngle >= 2 * np.pi:  # 角度>=360,重置角度，增加注释长度
                nowAngle = 0
                relatePos = (nowLenth + lengthInterval) / nowLenth * relatePos
            # 旋转矩阵
            rotateMatrix = np.array([
                [np.cos(nowAngle), -np.sin(nowAngle)],
                [np.sin(nowAngle), np.cos(nowAngle)]
            ])

            nowLenth = np.linalg.norm(relatePos)  # 当前注释长度
            nowAbsPos = rotateMatrix.dot(relatePos) + objPos  # 更新当前注释位置
            if nowLenth > max(self.radarCanvasW - textBlockW, self.radarCanvasH - textBlockH):  # 铁定要出画布了，暂时随便画
                return [self.radarCanvasW + textBlockW, textBlockH]

    def drawRadarDataByMatplotlib(self, savePath, radar_frame_tixy_history_list):
        objTrack = []
        for idx, track in enumerate(radar_frame_tixy_history_list):
            objTrack.append(
                [[self.worldToImageCofX(obj["position"][0]), self.worldToImageCofY(obj["position"][1])] for obj in
                 track["track"]])

        # # 20231229 只要画最长的轨迹
        # if len(objTrack)>0:
        #     objTrackMax = {0:[]}
        #     for track in objTrack.values():
        #         if len(track)>len(objTrackMax[0]):
        #             objTrackMax[0]=track
        #     objTrack=objTrackMax
        # 绘制
        drawElement = []
        drawedArea = []
        annotatePosY = 0
        colorMapNote = ColorMap(len(objTrack), "brg")

        pointSizePx = int(self.ptToPx(self.fontHeightPt / 8))
        lineSizePx = int(self.ptToPx(self.fontHeightPt / 10))

        fontHeightPx = int(self.ptToPx(self.fontHeightPt))
        fontWidthPx = int(self.ptToPx(self.fontWidthPt))
        font = 'consolas'

        for idx, track in enumerate(objTrack):
            track = np.array(track)
            x = track[:, 0]
            y = track[:, 1]
            # 渐变色
            # colorMap = ColorMap(len(track), "binary")
            # e0 = self.radarCanvasAx.scatter(x, y, c=colorMap.getColor(), cmap=colorMap.colorMap, s=(self.fontHeightPt / 8) ** 2)
            # 纯色
            e0 = self.radarCanvasAx.scatter(x, y, c="black", s=pointSizePx ** 2)  # s 会先开平方，所以先次方

            # trackPos = np.mean(track,axis=0) # 获取轨迹代表性点
            trackPos = track[0]  # 获取轨迹代表性点

            # 获取注释块中心点最终位置
            textBlockW = fontWidthPx * len(str(idx))  # 注释块宽
            textBlockH = fontHeightPx * len(str(idx))  # 注释块高
            textBlockPos = self.surePos(trackPos, drawedArea, textBlockW, textBlockH)

            drawedArea.append(trackPos)  # 数据位置也不能挡
            drawedArea.append(textBlockPos)

            # data表示xytext以xy数据所在的坐标系为坐标系
            e1 = self.radarCanvasAx.annotate(f'{idx}', color=colorMapNote(idx), xy=trackPos, xytext=textBlockPos,
                                             textcoords='data', fontsize=self.fontHeightPt, ha='center', va='center',
                                             fontname=font,
                                             arrowprops=dict(arrowstyle="->", linewidth=lineSizePx,
                                                             color=colorMapNote(idx)))

            if self.ptToPx(-annotatePosY) > (self.radarCanvasAxLocate[3] - self.radarCanvasAxLocate[1]):
                e2 = self.radarCanvasAx.annotate(
                    f'  ......',
                    xy=(self.radarCanvasW, self.radarCanvasH), xytext=(0, annotatePosY), fontsize=self.fontHeightPt,
                    color='red', xycoords='data', textcoords='offset points', va='center', fontname=font,
                    annotation_clip=False)
            else:
                xText = f"{self.imageToWorldCofX(x[0]):.1f}".rjust(5)
                yText = f"{self.imageToWorldCofY(y[0]):.1f}".rjust(5)
                e2 = self.radarCanvasAx.annotate(
                    f'  id{idx}:\n    positon:({xText},{yText})',
                    xy=(self.radarCanvasW, self.radarCanvasH), xytext=(0, annotatePosY), fontsize=self.fontHeightPt,
                    color='red', xycoords='data', textcoords='offset points', va='top', fontname=font,
                    annotation_clip=False)
                annotatePosY -= (self.fontHeightPt * 3)
            drawElement.append(e0)
            drawElement.append(e1)
            drawElement.append(e2)

        # 去除白边，保存图片
        directoryPath = os.path.dirname(savePath)
        if not os.path.exists(directoryPath):
            os.mkdir(directoryPath)
        print('drawRadarDataByMatplotlib savePath=' + savePath)
        self.radarCanvasAx.figure.savefig(savePath)
        # plt.show()
        for e in drawElement:
            e.remove()

        return np.array(Image.open(savePath))
        # 将图像转换为NumPy数组

    def drawRadarDataByPillow(self, savePath, radar_frame_tixy_history_list, tickle):
        templateCopy = self.template.copy()
        # templateCopy= Image.open(self.template_png_path)
        draw = ImageDraw.Draw(templateCopy)
        objTrack = []
        for idx, track in enumerate(radar_frame_tixy_history_list):
            # print([obj["position"] for obj in track["track"]],"tradsf1")
            objTrack.append([[self.pilWorldToImageCofX(obj["position"][0]),self.pilWorldToImageCofY(obj["position"][1])] for obj in track["track"]])
            # print(objTrack[-1], "tradsf2")
            # print( [[self.pilImageToWorldCofX(obj[0]),self.pilWorldToImageCofX(obj[1])  ]for obj in objTrack[-1]])


        # # 20231229 只要画最长的轨迹
        # if len(objTrack)>0:
        #     objTrackMax = {0:[]}
        #     for track in objTrack.values():
        #         if len(track)>len(objTrackMax[0]):
        #             objTrackMax[0]=track
        #     objTrack=objTrackMax


        # 绘制
        drawedArea = []
        annotatePosY = self.radarCanvasAxLocate[1]

        pointSizePx = int(self.ptToPx(self.fontHeightPt / 8))
        lineSizePx = int(self.ptToPx(self.fontHeightPt / 10))

        fontHeightPx = int(self.ptToPx(self.fontHeightPt))
        fontWidthPx = int(self.ptToPx(self.fontWidthPt))

        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", fontHeightPx)
        colorMapNote = ColorMap(len(objTrack), "brg")
        noteGetColor = lambda idx: tuple(int(i * 255) for i in colorMapNote(idx)[:3])
        # colorMapTrack = ColorMap(len(objTrack),"binary")
        # trackGetColor = lambda idx: tuple(int(i * 255) for i in colorMapTrack(idx)[:3])
        for idx, track in enumerate(objTrack):
            track = np.array(track)
            for  t in track:
                x, y = t
                # 渐变色
                # draw.ellipse(((x-pointSizePx, y-pointSizePx), (x+pointSizePx, y+pointSizePx)), fill=trackGetColor(iidx))
                # 纯色
                draw.ellipse(((x - pointSizePx, y - pointSizePx), (x + pointSizePx, y + pointSizePx)), fill=(0, 0, 0))

            # trackPos = np.mean(track,axis=0) # 获取轨迹代表性点
            trackPos = track[0]  # 获取轨迹代表性点

            # 获取注释块中心点最终位置
            textBlockW = fontWidthPx * len(str(idx))  # 注释块宽
            textBlockH = fontHeightPx * len(str(idx))  # 注释块高
            textBlockPos = self.surePos(trackPos, drawedArea, textBlockW, textBlockH)

            drawedArea.append(trackPos)  # 数据位置也不能挡
            drawedArea.append(textBlockPos)

            # pillow文本是以左上角为中心点，故绘制位置需要偏移，且y轴和radarCanvas是反的
            textBlockDrawPos = (
            textBlockPos[0] - len(str(idx)) * fontWidthPx * 0.5, 2 * trackPos[1] - textBlockPos[1] - fontHeightPx * 0.5)
            draw.text(xy=textBlockDrawPos, text=f"{idx}", fill=noteGetColor(idx), font=font)
            # 线不用偏移，但要短一点
            textLinePos = textBlockPos - (textBlockPos - trackPos) * (
                        fontHeightPx / np.linalg.norm(textBlockPos - trackPos))
            textLinePos[1] = 2 * trackPos[1] - textLinePos[1]
            draw.line([trackPos[0], trackPos[1], textLinePos[0], textLinePos[1]], fill=noteGetColor(idx),
                      width=lineSizePx)

            if annotatePosY >= self.radarCanvasAxLocate[3]:
                draw.text(xy=(self.radarCanvasAxLocate[2], annotatePosY),
                          text=f'  ......',
                          fill=(255, 0, 0), font=font)
            else:
                xText = f"{self.pilImageToWorldCofX(track[0, 0]):.1f}".rjust(5)
                yText = f"{self.pilImageToWorldCofY(track[0, 1]):.1f}".rjust(5)

                # for i in [45, 55, 95, 105, 145, 155, 195, 205]:
                #     if abs(tickle - i) <= 5 and :
                #         tickle = i
                less=[(40, 45),  (90, 95)  ,  (140, 145), (190, 195)]
                more=[(55, 60),  (105, 110),  (155, 160), (205, 210)]
                for l,m in zip(less,more):
                    if l[0]<=tickle<=l[1]:
                        tickle = l[1]
                        break
                    elif m[0]<=tickle<=m[1]:
                        tickle = m[0]
                        break


                draw.text(xy=(self.radarCanvasAxLocate[2], annotatePosY),
                          text=f'  id{idx}:\n    positon:({xText},{tickle:.1f})',
                          fill=(255, 0, 0), font=font)
                annotatePosY += (fontHeightPx * 3)
        # 去除白边，保存图片
        directoryPath = os.path.dirname(savePath)
        if not os.path.exists(directoryPath):
            os.mkdir(directoryPath)
        templateCopy.save(savePath)
        return np.array(templateCopy)
        # except Exception as e:
        #     print('图片保存失败',e)

    def drawRadarData(self, savePath, radar_frame_tixy_history_list,tickle):
        s=time.time()
        if self.using_pillow:
            try:
                self.drawRadarDataByPillow(savePath, radar_frame_tixy_history_list,tickle)

            except:
                print(f"error:{traceback.format_exc()}")
                self.using_pillow = False
                self.drawRadarDataByMatplotlib(savePath, radar_frame_tixy_history_list)
        else:
            self.drawRadarDataByMatplotlib(savePath, radar_frame_tixy_history_list)

if __name__ == "__main__":
    defences = [[
        [-3.7483939446315917, 0],
        [-10.492263740617746, 28.796109566705628],
        [-10.434912389482123, 113.23762313573822],
        [0.05222912089276654, 107.12265534038852],
        [-0.8228577938721543, 0]],
        [[-4.019244391530302, 0],
         [-7.204639577639635, 93.84449208361869],
         [0.015105168952314979, 284.60045142546113],
         [9.542230479051248, 284.60045142546113],
         [0.7106734246990943, 0]]]
    # defences=[[[-3.264345210858225, 0], [-3.7655586325916004, 0], [-2.67645769398247, 12.864428024516446], [-2.30382134339379, 43.989961190294906], [1.6755697908315175, 47.079944340766694], [0.9965294393171281, 0]], [[-1.8499487072838992, 0], [-1.214983855542025, 95.79801612425173], [2.7982116909832393, 99.53119408342528], [1.7336426378114658, 0]]]
    print('aa')
    a = RadarDisplay(defences=defences)
    x = time.time()
    a.drawRadarDataByPillow("./a/pillow.png",
                            {3129: [[1692601594.9606776, -2.5890909042780206, 44.579105063800739],
                                    [1692601595.0849257, -2.5829827817939148, 43.87913171370824],
                                    [1692601595.2063456, -2.4786236442920533, 43.380023338282754],
                                    [1692601595.3297784, -2.4760058775131513, 43.080034759671683],
                                    [1692601595.4643686, -2.4742606996605496, 42.880042373930962],
                                    [1692601595.5872867, -2.4733881107342488, 42.780046181060605],
                                    [1692601595.7151206, -2.4733881107342488, 42.780046181060605],
                                    [1692601595.8428748, -2.4733881107342488, 42.780046181060605],
                                    [1692601595.9737833, -2.4742606996605496, 42.880042373930962],
                                    [1692601596.1019533, -2.4742606996605496, 42.880042373930962],
                                    [1692601596.2344434, -2.4751332885868504, 42.980038566801326],
                                    [1692601596.358982, -2.4751332885868504, 42.980038566801326], [
                                        1692601596.498201, -2.5760020703835087, 43.079162170745384],
                                    [1692601596.6158154, -2.5760020703835087, 43.079162170745384],
                                    [1692601596.7425056, -2.5751294814572079, 42.97916597787502],
                                    [1692601596.8697042, -2.5690213589731021, 42.279192627782521],
                                    [1692601596.9960952, -2.4646622214712406, 41.780084252357035],
                                    [1692601597.1466768, -2.4620444546923381, 41.480095673745964],
                                    [1692601597.2661943, -2.4602992768397365, 41.280103288005243],
                                    [1692601597.382531, -2.5594228807837931, 41.179234506208594],
                                    [1692601597.5099907, -2.5594228807837931, 41.179234506208594],
                                    [1692601597.639093, -2.5594228807837931, 41.179234506208594],
                                    [1692601597.762553, -2.5602954697100939, 41.279230699078944],
                                    [1692601597.8977618, -2.5602954697100939, 41.279230699078944],
                                    [1692601598.0224977, -2.5611680586363947, 41.379226891949301],
                                    [1692601598.1621234, -2.5611680586363947, 41.379226891949301],
                                    [1692601598.2817554, -2.6611642515067517, 41.378354303023002],
                                    [1692601598.4040186, -2.6620368404330526, 41.478350495893359],
                                    [1692601598.5314076, -2.6620368404330526, 41.478350495893359],
                                    [1692601598.6730914, -2.6611642515067517, 41.378354303023002],
                                    [1692601598.8058271, -2.655056129022646, 40.67838095293051],
                                    [1692601598.9542387, -2.5506969915207853, 40.179272577505024],
                                    [1692601599.0530396, -2.5480792247418829, 39.879283998893946],
                                    [1692601599.1738179, -2.5463340468892812, 39.679291613153232],
                                    [1692601599.303677, -2.5454614579629804, 39.579295420282875],
                                    [1692601599.4344685, -2.5454614579629804, 39.579295420282875],
                                    [1692601599.5627012, -2.5454614579629804, 39.579295420282875],
                                    [1692601599.6919894, -2.5463340468892812, 39.679291613153232],
                                    [1692601599.815254, -2.5463340468892812, 39.679291613153232],
                                    [1692601599.940758, -2.547206635815582, 39.779287806023589],
                                    [1692601600.0757277, -2.5463340468892812, 39.679291613153232]],
                             31234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                     ], 65: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                             [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                             [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                             [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                             [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                             [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                             [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                             [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                             [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                             [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                             [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                             ], 4234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                       [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                       [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                       [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                       [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                       [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                       [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                       [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                       ],
                             22: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                  [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                  [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                  [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                  [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                  [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                  [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                  [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                  ],
                             1: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                 [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                 [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                 [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                 [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                 [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                 [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                 [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                 [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                 [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                 [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                 ], 311: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                          [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                          [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                          [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                          [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                          [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                          ], 31235: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                     ],
                             31236: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                     ],
                             31237: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                     ], 312386: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                 [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                 [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                 [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                 [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                 [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                 [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                 [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                 ],
                             312382: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                      [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                      [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                      [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                      [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                      [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                      ],
                             31231282: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                        [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                        [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                        [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                        [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                        [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                        [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                        [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                        [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                        [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                        [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                        ],
                             12: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                  [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                  [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                  [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                  [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                  [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                  [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                  [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                  [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                  ], 14: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                          [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                          [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                          [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                          [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                          [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                          ], 655: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                   [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                   [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                   [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                   [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                   [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                   [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                   [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                   [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                   [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                   [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                   ], 98: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                           [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                           [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                           [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                           [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                           [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                           [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                           [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                           ]
                             })
    print("pillow 516x600", time.time() - x)
    x = time.time()
    a.drawRadarDataByMatplotlib("./a/matplotlib.png",
                                {3129: [[1692601594.9606776, -2.5890909042780206, 44.579105063800739],
                                        [1692601595.0849257, -2.5829827817939148, 43.87913171370824],
                                        [1692601595.2063456, -2.4786236442920533, 43.380023338282754],
                                        [1692601595.3297784, -2.4760058775131513, 43.080034759671683],
                                        [1692601595.4643686, -2.4742606996605496, 42.880042373930962],
                                        [1692601595.5872867, -2.4733881107342488, 42.780046181060605],
                                        [1692601595.7151206, -2.4733881107342488, 42.780046181060605],
                                        [1692601595.8428748, -2.4733881107342488, 42.780046181060605],
                                        [1692601595.9737833, -2.4742606996605496, 42.880042373930962],
                                        [1692601596.1019533, -2.4742606996605496, 42.880042373930962],
                                        [1692601596.2344434, -2.4751332885868504, 42.980038566801326],
                                        [1692601596.358982, -2.4751332885868504, 42.980038566801326], [
                                            1692601596.498201, -2.5760020703835087, 43.079162170745384],
                                        [1692601596.6158154, -2.5760020703835087, 43.079162170745384],
                                        [1692601596.7425056, -2.5751294814572079, 42.97916597787502],
                                        [1692601596.8697042, -2.5690213589731021, 42.279192627782521],
                                        [1692601596.9960952, -2.4646622214712406, 41.780084252357035],
                                        [1692601597.1466768, -2.4620444546923381, 41.480095673745964],
                                        [1692601597.2661943, -2.4602992768397365, 41.280103288005243],
                                        [1692601597.382531, -2.5594228807837931, 41.179234506208594],
                                        [1692601597.5099907, -2.5594228807837931, 41.179234506208594],
                                        [1692601597.639093, -2.5594228807837931, 41.179234506208594],
                                        [1692601597.762553, -2.5602954697100939, 41.279230699078944],
                                        [1692601597.8977618, -2.5602954697100939, 41.279230699078944],
                                        [1692601598.0224977, -2.5611680586363947, 41.379226891949301],
                                        [1692601598.1621234, -2.5611680586363947, 41.379226891949301],
                                        [1692601598.2817554, -2.6611642515067517, 41.378354303023002],
                                        [1692601598.4040186, -2.6620368404330526, 41.478350495893359],
                                        [1692601598.5314076, -2.6620368404330526, 41.478350495893359],
                                        [1692601598.6730914, -2.6611642515067517, 41.378354303023002],
                                        [1692601598.8058271, -2.655056129022646, 40.67838095293051],
                                        [1692601598.9542387, -2.5506969915207853, 40.179272577505024],
                                        [1692601599.0530396, -2.5480792247418829, 39.879283998893946],
                                        [1692601599.1738179, -2.5463340468892812, 39.679291613153232],
                                        [1692601599.303677, -2.5454614579629804, 39.579295420282875],
                                        [1692601599.4344685, -2.5454614579629804, 39.579295420282875],
                                        [1692601599.5627012, -2.5454614579629804, 39.579295420282875],
                                        [1692601599.6919894, -2.5463340468892812, 39.679291613153232],
                                        [1692601599.815254, -2.5463340468892812, 39.679291613153232],
                                        [1692601599.940758, -2.547206635815582, 39.779287806023589],
                                        [1692601600.0757277, -2.5463340468892812, 39.679291613153232]],
                                 31234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                         [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                         [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                         [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                         [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                         [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                         ], 65: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                 [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                 [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                 [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                 [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                 [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                 [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                 [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                 [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                 ], 4234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                           [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                           [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                           [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                           [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                           [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                           [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                           [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                           [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                           ],
                                 22: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                      [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                      [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                      [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                      [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                      [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                      ],
                                 1: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                     ], 311: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                              [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                              [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                              [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                              [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                              [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                              [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                              [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                              ], 31235: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                         [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                         [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                         [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                         [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                         [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                         [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                         [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                         [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                         [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                         [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                         ],
                                 31236: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                         [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                         [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                         [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                         [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                         [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                         ],
                                 31237: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                         [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                         [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                         [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                         [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                         [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                         ], 312386: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                     ],
                                 312382: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                          [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                          [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                          [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                          [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                          [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                          [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                          [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                          ],
                                 31231282: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                            [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                            [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                            [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                            [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                            [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                            [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                            [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                            [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                            [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                            [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                            ],
                                 12: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                      [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                      [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                      [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                      [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                      [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                      ], 14: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                              [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                              [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                              [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                              [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                              [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                              [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                              [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                              [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                              ], 655: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                                       [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                                       [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                                       [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                                       [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                                       [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                                       [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                                       [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                                       [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                                       ],
                                 98: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                      [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                      [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                      [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                      [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                      [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                      [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                      [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                      ]
                                 })
    print("matplotlib 516x600", time.time() - x)
    time.sleep(121212)
    # pillow 516x600 0.04637742042541504
    # matplotlib 516x600 0.09035444259643555

    # pillow 1355x2160 0.27976346015930176
    # matplotlib 1355x2160 0.212431907653808

    #
    # a.drawRadarData("./a/xyp2.png",
    #                 {31234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
    #                          [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
    #                          [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
    #                          [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
    #                          [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
    #                          [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
    #                          [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
    #                          [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
    #                          [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
    #                          [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
    #                          [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
    #                          ]})
    # a.drawRadarData("./a/xyp3.png",{})
    # plt.show()

    a.drawRadarDataByMatplotlib("./a/xyp1.png",
                                {31234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                         [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                         [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                         [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                         [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                         [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                         [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                         [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                         ]})
    a.drawRadarDataByPillow("./a/xyp2.png",
                            {31234: [[1692601594.9606776, 5.5890909042780206, 44.579105063800739],
                                     [1692601595.0849257, 5.5829827817939148, 43.87913171370824],
                                     [1692601595.2063456, 5.4786236442920533, 43.380023338282754],
                                     [1692601595.3297784, 5.4760058775131513, 43.080034759671683],
                                     [1692601595.4643686, 5.4742606996605496, 42.880042373930962],
                                     [1692601595.5872867, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.7151206, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.8428748, 5.4733881107342488, 42.780046181060605],
                                     [1692601595.9737833, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.1019533, 5.4742606996605496, 42.880042373930962],
                                     [1692601596.2344434, 5.4751332885868504, 42.980038566801326],
                                     ]})
