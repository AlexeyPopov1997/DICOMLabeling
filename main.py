import sys
import cv2
import math
import SimpleITK as stk

from enum import Enum
from PyQt5.QtCore import QPoint, QRect, QSize, pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QPixmap, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QComboBox, QLabel, QProgressBar, QHBoxLayout, QWidget, \
                            QRubberBand, QFileDialog

from src.dicom_image import DicomImage
from src.bounding_box import BoundingBox
from src.viewer import Viewer, Mode, Label, AppString
from src.display_image_container import DisplayImageContainer, Utils


class MainUI(object):
    def __init__(self):
        self.windowWidth = 500
        self.windowHeight = 530
        self.windowTitle = AppString.TITLE.value
        self.windowXPos = 300
        self.windowYPos = 200
        self.allowImageType = '(*.dcm)'

    def setup_ui(self):
        self.loadFileBtn = QAction(QIcon('./icons/open.png'), '', self)
        self.loadFileBtn.setIconText(AppString.LOADFILE.value)
        self.saveBtn = QAction(QIcon('./icons/save.png'), '', self, shortcut="Ctrl+S")
        self.saveBtn.setIconText(AppString.SAVE.value)
        self.labelComboBox = QComboBox()

        self.remaining = QLabel('| Remaining: ')
        self.pbarLoad = QProgressBar(self)
        self.pbarLoad.setFixedWidth(300)
        self.imageIdx = QLabel(' 1/120')

        remainingLayout = QHBoxLayout()
        remainingLayout.addWidget(self.remaining, 0)
        remainingLayout.addWidget(self.pbarLoad, 0)
        remainingLayout.addWidget(self.imageIdx, 1)
        remainingLayout.setContentsMargins(0, 0, 0, 0)
        self.remainingNotification = QWidget()
        self.remainingNotification.setLayout(remainingLayout)
        self.remainingNotification.hide()

        self.toolbar = self.addToolBar('ToolBar')
        self.toolbar.setMovable(False)
        self.toolbar.addActions([self.loadFileBtn, self.saveBtn])

        for action in self.toolbar.actions():
            widget = self.toolbar.widgetForAction(action)
            widget.setFixedSize(160, 60)

        self.toolbar.addWidget(self.labelComboBox)

        self.toolbar.setIconSize(QSize(30, 30))
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon | Qt.AlignLeading)
        self.toolbar.setStyleSheet('QToolBar {padding-right: 30px;}')

        self.viewer = Viewer(self)
        self.viewer.setScaledContents(True)
        self.viewer.setFocusPolicy(Qt.StrongFocus)

        self.notification = QLabel(Mode.LABELING.name, self)
        self.notification.setStyleSheet('background-color: rgb(0, 255, 0)')
        self.boundingBoxNum = QLabel('| Bounding Box: 0')

        self.description = QLabel('')
        self.pbar = QProgressBar(self)
        self.pbar.setMaximumWidth(300)
        self.pbar.hide()

        self.bottomBar = self.statusBar()
        self.bottomBar.setStyleSheet("background-color: rgb(200, 200, 200)")
        self.bottomBar.addWidget(self.notification)
        self.bottomBar.addWidget(self.boundingBoxNum)
        self.bottomBar.addWidget(self.remainingNotification)
        self.bottomBar.addPermanentWidget(self.description)
        self.bottomBar.addPermanentWidget(self.pbar)

        self.setCentralWidget(self.viewer)
        self.setGeometry(self.windowXPos, self.windowYPos, self.windowWidth, self.windowHeight)
        self.setWindowTitle(self.windowTitle)


class Labeling(QMainWindow, MainUI):
    dicomImage: DicomImage

    def __init__(self):
        super().__init__()
        Utils.change_cursor(Qt.WaitCursor)
        self.setup_ui()
        self.setMinimumSize(self.windowWidth, self.windowHeight)
        self.loadFileBtn.triggered.connect(self.open_file_dialogue)
        self.saveBtn.triggered.connect(self.save_file_dialogue)
        self.viewer.changeBoxNum.connect(self.change_box_num)

        for label in Label:
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor(self.viewer.colorTable[label]))
            self.labelComboBox.addItem(QIcon(pixmap), label.value)

        self.labelComboBox.setCurrentIndex(len(Label) - 1)
        self.labelComboBox.currentTextChanged.connect(self.viewer.set_label)
        self.labelComboBox.setCurrentIndex(0)
        self.show()
        self.setFocus()
        self.loadImage = None
        self.dicomImage = None
        Utils.change_cursor(Qt.ArrowCursor)

    def initialize(self):
        self.labelComboBox.setCurrentIndex(0)
        self.change_box_num(0)
        self.pbarLoad.setValue(0)
        self.loadImage = None
        self.dicomImage = None
        self.remainingNotification.hide()
        self.imageIdx.setText('')

    def keyPressEvent(self, QKeyEvent):
        if not self.viewer.makeBoundingBox and self.viewer.correctionMode == CorrectionMode.OTHER:
            if QKeyEvent.key() == Qt.Key_I:
                self.viewer.mode = Mode.CORRECTION
                self.viewer.mouseLineVisible = False
            elif QKeyEvent.key() == Qt.Key_Escape:
                self.viewer.mode = Mode.LABELING
                self.viewer.mouseLineVisible = True
            elif QKeyEvent.key() == Qt.Key_Shift:
                self.viewer.mode = Mode.CORRECTION
                self.viewer.mouseLineVisible = False
            self.__change_mode_label(self.viewer.mode)

        if QKeyEvent.key() == Qt.Key_Delete:
            if self.viewer.mode == Mode.CORRECTION:
                self.viewer.remove_bounding_box()

        super().keyPressEvent(QKeyEvent)

    def keyReleaseEvent(self, QKeyEvent):
        if not self.viewer.makeBoundingBox and self.viewer.correctionMode == CorrectionMode.OTHER:
            if QKeyEvent.key() == Qt.Key_Shift:
                self.viewer.mode = Mode.LABELING
                self.viewer.mouseLineVisible = True
                self.__change_mode_label(self.viewer.mode)
                Utils.change_cursor(Qt.ArrowCursor)
        elif self.viewer.correctionMode != CorrectionMode.OTHER:
            if QKeyEvent.key() == Qt.Key_Shift:
                self.__change_mode_label(Mode.LABELING)
                self.viewer.shiftFlag = True

    @pyqtSlot(int)
    def change_box_num(self, num):
        self.boundingBoxNum.setText('| Bounding Box: {}'.format(num))

    def open_file_dialogue(self):
        imagePath, fileType = QFileDialog.getOpenFileName(self, 'Select Image', '',
                                                          'Image files {}'.format(self.allowImageType),
                                                          options=QFileDialog.DontUseNativeDialog)

        if imagePath != '':
            img = stk.ReadImage(imagePath)
            img = stk.IntensityWindowing(img, -1000, 1000, 0, 255)
            img = stk.Cast(img, stk.sitkUInt8)
            stk.WriteImage(img, "./.temp/temp.png")
            rawImage = QImage('./.temp/temp.png')

            self.initialize()
            self.viewer.initialize()
            self.loadImage = DisplayImageContainer(rawImage, imagePath)
            self.dicomImage = DicomImage(rawImage, imagePath)
            self.viewer.setPixmap(QPixmap.fromImage(rawImage.scaled(self.viewer.width(), self.viewer.height())))

    def save_file_dialogue(self):
        if self.dicomImage is not None:
            dicomImageName = self.dicomImage.fileName.split('.')[0] + '.dcm'
            savePath, fileType = QFileDialog.getSaveFileName(self, 'Save', dicomImageName,
                                                             'dicom files {}'.format('*.dcm'))

            if fileType != '':
                if savePath.split('/')[-1].split('.')[-1] != 'dcm':
                    savePath += '.dcm'

                self.__save_to_dicom(savePath)

                pixmap = QPixmap(self.viewer.width(), self.viewer.height())
                pixmap.fill(QColor(Qt.gray))
                self.viewer.setPixmap(pixmap)

                self.initialize()
                self.viewer.initialize()

    def __save_to_dicom(self, filePath):
        bndBox = self.viewer.boxes

        overlaysInfo = []

        for box in bndBox:
            x_min, y_min, width, height, label = box
            positionRatio = (x_min / self.viewer.width(), y_min / self.viewer.height())
            scaleRatio = (width / self.viewer.width(), height / self.viewer.height())

            bbox_x_min = self.dicomImage.imageWidth * positionRatio[0]
            bbox_y_min = self.dicomImage.imageHeight * positionRatio[1]
            bbox_x_max = bbox_x_min + self.dicomImage.imageWidth * scaleRatio[0]
            bbox_y_max = bbox_y_min + self.dicomImage.imageHeight * scaleRatio[1]

            bbox_x_min = max(0, min(math.floor(bbox_x_min), self.dicomImage.imageWidth - 1))
            bbox_y_min = max(0, min(math.floor(bbox_y_min), self.dicomImage.imageHeight - 1))
            bbox_x_max = max(0, min(math.ceil(bbox_x_max), self.dicomImage.imageWidth - 1))
            bbox_y_max = max(0, min(math.ceil(bbox_y_max), self.dicomImage.imageHeight - 1))

            overlaysInfo.append({'bbox': [bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max], 'category_id': label.value})

        for overlayInfo in overlaysInfo:
            overlay_bbox = self.dicomImage.create_overlay_box(overlayInfo['bbox'][0],
                                                              overlayInfo['bbox'][1],
                                                              overlayInfo['bbox'][2],
                                                              overlayInfo['bbox'][3])

            self.dicomImage.add_overlay(overlayInfo['category_id'], overlay_bbox)

        return self.dicomImage.image.save_as(filePath)

    def __change_mode_label(self, mode):
        if mode == Mode.CORRECTION:
            self.notification.setText(Mode.CORRECTION.name)
            self.notification.setStyleSheet('QWidget { background-color: %s }' % (QColor(255, 0, 0).name()))
        elif mode == Mode.LABELING:
            self.notification.setText(Mode.LABELING.name)
            self.notification.setStyleSheet('QWidget { background-color: %s }' % (QColor(0, 255, 0).name()))

    def __frame_extraction(self, video_path):
        video_name = os.path.basename(video_path).split('.')[0]
        video_directory = os.path.dirname(video_path)
        destination_path = os.path.join(video_directory, video_name)
        os.makedirs(destination_path, exist_ok=True)

        self.description.setText('Frame extraction ')
        self.pbar.show()
        self.pbar.setValue(0)

        cnt = 0
        cap = cv2.VideoCapture(video_path)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        data_length = int(0.05 * length)
        using_idx = np.array(random.sample(range(length), data_length))

        while cap.isOpened():
            ret, frame = cap.read()

            if ret:
                if cnt in using_idx:
                    Image.fromarray(frame[..., ::-1]).save(
                        os.path.join(destination_path, '{}_{}.jpg'.format(video_name, cnt)))
                cnt += 1
                percent = (cnt + 1) / length * 100
                self.pbar.setValue(percent)
            else:
                break

        cap.release()

        self.description.setText('')
        self.pbar.hide()

        return destination_path


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Labeling()
    sys.exit(app.exec_())
