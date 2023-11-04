import json
from load_fit import load_fit, get_gps_data
# PyQt5 imports
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSlider, QApplication, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import sys
import os

fit_file_path = 'data/Lunch_Ride.fit'
# df = load_fit(fit_file_path)
# print(df['timestamp'])
# 假设这是你的GPS坐标列表，格式是[(纬度, 经度), ...]
gps_coordinates = get_gps_data(fit_file_path)
print(gps_coordinates)


class MapWindow(QMainWindow):
    def __init__(self, gps_coordinates):
        super().__init__()
        self.gps_coordinates = gps_coordinates
        self.fps = 30
        self.fit_gap = 1
        self.video_slider_position = 0
        self.map_slider_position = 0
        self.user_is_interacting = True
        self.frame_duration = 200
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Map and Video Viewer")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout()  # Change to QHBoxLayout to add widgets side by side
        self.central_widget.setLayout(self.main_layout)

        # Map Layout
        self.map_layout = QVBoxLayout()
        self.map_view = QWebEngineView()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.map_view.load(QUrl.fromLocalFile(os.path.join(dir_path, "map.html")))
        self.map_view.loadFinished.connect(self.initMap)
        self.map_slider = QSlider(Qt.Horizontal)
        self.map_slider.setMinimum(0)
        self.map_slider.setMaximum(len(self.gps_coordinates) - 1)
        self.map_slider.valueChanged.connect(self.sliderMoved)
        self.map_layout.addWidget(self.map_view)
        self.map_layout.addWidget(self.map_slider)

        # Video Layout
        self.video_layout = QVBoxLayout()
        self.video_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(0, 0)
        self.video_slider.sliderMoved.connect(self.setPosition)
        self.video_layout.addWidget(self.video_widget)
        self.video_layout.addWidget(self.video_slider)
        self.play_pause_button = QPushButton("播放/暂停")
        self.play_pause_button.clicked.connect(self.togglePlayPause)
        self.video_layout.addWidget(self.play_pause_button)

        # Load video
        video_path = "C:/李峥昊/学习/项目/VIRB/video/GH010288~1.mp4"
        self.video_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        # self.video_player.play()
        self.video_player.positionChanged.connect(self.positionChanged)
        self.video_player.durationChanged.connect(self.durationChanged)

        # Add map_layout and video_layout to main_layout
        self.main_layout.addLayout(self.video_layout)
        self.main_layout.addLayout(self.map_layout)

    def initMap(self):
        code = f"initMap({self.gps_coordinates[0][0]}, {self.gps_coordinates[0][1]}, {19});"
        self.map_view.page().runJavaScript(code)
        code = f"initMapTrack({json.dumps(self.gps_coordinates)});"
        self.map_view.page().runJavaScript(code)

    @pyqtSlot(int)
    def sliderMoved(self, position):
        if self.user_is_interacting:
            self.map_slider_position = position
            self.video_slider_position = self.video_slider.value()
            print(f'map_slider主动更新：当前视频位置{self.video_slider_position / 1000}s,'
                  f' 当前gps位置{self.map_slider_position * self.fit_gap}s')
        lat = self.gps_coordinates[position][0]
        lon = self.gps_coordinates[position][1]
        self.updateMap(lat, lon)
        # Link the map slider to the video slider if needed
        # self.video_player.setPosition(position * (self.video_player.duration() / len(self.gps_coordinates)))

    def updateMap(self, lat, lon):
        code = f"updateMapWithNewData({lat}, {lon});"
        self.map_view.page().runJavaScript(code)

    def togglePlayPause(self):
        if self.video_player.state() == QMediaPlayer.PlayingState:
            self.video_player.pause()
        else:
            self.video_player.play()

    def positionChanged(self, position):
        self.video_slider.setValue(position)
        # Link the map slider to the video slider if needed
        self.user_is_interacting = False
        map_add_position = int((position - self.video_slider_position) * self.fit_gap / 1000)
        new_map_slider_position = self.map_slider_position + map_add_position
        lat = self.gps_coordinates[new_map_slider_position][0]
        lon = self.gps_coordinates[new_map_slider_position][1]
        self.updateMap(lat, lon)
        self.map_slider.setSliderPosition(new_map_slider_position)
        print(f'map_slider联动更新：当前视频位置{position / 1000}s,'
              f' 当前gps位置{new_map_slider_position * self.fit_gap}s')
        self.user_is_interacting = True

    def durationChanged(self, duration):
        self.video_slider.setRange(0, duration)

    def setPosition(self, position):
        self.video_player.setPosition(position)


# Set up the application and window
app = QApplication(sys.argv)
window = MapWindow(gps_coordinates)
window.show()
sys.exit(app.exec_())
