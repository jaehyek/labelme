# -*- coding: utf-8 -*-

import functools
import math
import os
import os.path as osp
import re
import webbrowser

import imgviz
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy import QtWidgets

from labelme import __appname__
from labelme import PY2
from labelme import QT5

from . import utils
from labelme.config import get_config
from labelme.label_file import LabelFile
from labelme.label_file import LabelFileError
from labelme.logger import logger
from labelme.shape import Shape
from labelme.widgets import BrightnessContrastDialog
from labelme.widgets import Canvas
from labelme.widgets import LabelDialog
from labelme.widgets import LabelListWidget
from labelme.widgets import LabelListWidgetItem
from labelme.widgets import ToolBar
from labelme.widgets import UniqueLabelQListWidget
from labelme.widgets import ZoomWidget


# FIXME
# - [medium] Set max zoom value to something big enough for FitWidth/Window

# TODO(unknown):
# - [high] Add polygon movement with arrow keys
# - [high] Deselect shape when clicking and already selected(?)
# - [low,maybe] Preview images on file dialogs.
# - Zoom is too "steppy".


LABEL_COLORMAP = imgviz.label_colormap(value=200)


class MainWindow(QtWidgets.QMainWindow):

    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(self, dict_config=None, filename=None, output=None, output_file=None, output_dir=None, ):
        if output is not None:
            logger.warning( "argument output is deprecated, use output_file instead" )
            if output_file is None:
                output_file = output

        # see labelme/config/default_config.yaml for valid configuration
        if dict_config is None:
            dict_config = get_config()
        self._dict_config = dict_config

        # set default shape colors
        Shape.line_color = QtGui.QColor(*self._dict_config["shape"]["line_color"])       # r,g,b,alpha 값이다.
        Shape.fill_color = QtGui.QColor(*self._dict_config["shape"]["fill_color"])
        Shape.select_line_color = QtGui.QColor(*self._dict_config["shape"]["select_line_color"])
        Shape.select_fill_color = QtGui.QColor(*self._dict_config["shape"]["select_fill_color"])
        Shape.vertex_fill_color = QtGui.QColor(*self._dict_config["shape"]["vertex_fill_color"])
        Shape.hvertex_fill_color = QtGui.QColor(*self._dict_config["shape"]["hvertex_fill_color"])

        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False

        # Main widgets and related state.
        self.labelDialog = LabelDialog(
            parent=self,
            labels=self._dict_config["labels"],
            sort_labels=self._dict_config["sort_labels"],
            show_text_field=self._dict_config["show_label_text_field"],
            completion=self._dict_config["label_completion"],
            fit_to_content=self._dict_config["fit_to_content"],
            flags=self._dict_config["label_flags"],
        )

        self.lastOpenDir = None

        ## digit0 ~ 9 까지 radio button 추가 .

        # self.digit_selected = -1
        #
        # self.layout_hdigit0 = QtWidgets.QHBoxLayout()
        # self.layout_hdigit1 = QtWidgets.QHBoxLayout()
        # self.layout_vdigit = QtWidgets.QVBoxLayout()
        #
        # self.widget_vdigit = QtWidgets.QFrame(self)
        # self.widget_vdigit.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Raised)
        # self.widget_vdigit.setStyleSheet("background-color: rgb(100, 255, 255);")
        #
        # self.widget_digit_h0 = QtWidgets.QWidget(self)
        # self.widget_digit_h1 = QtWidgets.QWidget(self)
        #
        # self.widget_vdigit.setLayout(self.layout_vdigit)
        #
        # self.layout_vdigit.addWidget(self.widget_digit_h0)
        # self.layout_vdigit.addWidget(self.widget_digit_h1)
        #
        # self.widget_digit_h0.setLayout(self.layout_hdigit0)
        # self.widget_digit_h1.setLayout(self.layout_hdigit1)
        #
        # self.group_digits = QtWidgets.QButtonGroup(self.widget_vdigit)
        #
        # self.digit0 = QtWidgets.QRadioButton("0")
        # self.digit1 = QtWidgets.QRadioButton("1")
        # self.digit2 = QtWidgets.QRadioButton("2")
        # self.digit3 = QtWidgets.QRadioButton("3")
        # self.digit4 = QtWidgets.QRadioButton("4")
        # self.digit5 = QtWidgets.QRadioButton("5")
        # self.digit6 = QtWidgets.QRadioButton("6")
        # self.digit7 = QtWidgets.QRadioButton("7")
        # self.digit8 = QtWidgets.QRadioButton("8")
        # self.digit9 = QtWidgets.QRadioButton("9")
        #
        # self.group_digits.addButton(self.digit0)
        # self.group_digits.addButton(self.digit1)
        # self.group_digits.addButton(self.digit2)
        # self.group_digits.addButton(self.digit3)
        # self.group_digits.addButton(self.digit4)
        # self.group_digits.addButton(self.digit5)
        # self.group_digits.addButton(self.digit6)
        # self.group_digits.addButton(self.digit7)
        # self.group_digits.addButton(self.digit8)
        # self.group_digits.addButton(self.digit9)
        #
        # self.layout_hdigit0.addWidget(self.digit0)
        # self.layout_hdigit0.addWidget(self.digit1)
        # self.layout_hdigit0.addWidget(self.digit2)
        # self.layout_hdigit0.addWidget(self.digit3)
        # self.layout_hdigit0.addWidget(self.digit4)
        # self.layout_hdigit1.addWidget(self.digit5)
        # self.layout_hdigit1.addWidget(self.digit6)
        # self.layout_hdigit1.addWidget(self.digit7)
        # self.layout_hdigit1.addWidget(self.digit8)
        # self.layout_hdigit1.addWidget(self.digit9)
        #
        # self.dockwidget_digits = QtWidgets.QDockWidget(self.tr("Digits"), self)
        # self.dockwidget_digits.setObjectName("Digits")
        # self.dockwidget_digits.setWidget(self.widget_vdigit)
        #
        # self.group_digits.buttonClicked[int].connect(self.btnDigitClicked)



        ## flag widget
        self.dockwidget_flag = self.listwidget_flag = None
        self.dockwidget_flag = QtWidgets.QDockWidget(self.tr("Flags"), self)      # QObject.tr은 다중언어를 지원하기 위해서.
        self.dockwidget_flag.setObjectName("Flags")

        self.listwidget_flag = QtWidgets.QListWidget()
        if dict_config["flags"]:
            self.loadFlags({k: False for k in dict_config["flags"]})
        self.dockwidget_flag.setWidget(self.listwidget_flag)
        self.listwidget_flag.itemChanged.connect(self.canvas_shape_moved)

        # label widget
        self.listwidget_label = LabelListWidget()  # labelme.widgets.LabelListWidget
        self.listwidget_label.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.listwidget_label.itemDoubleClicked.connect(self.editLabel)
        self.listwidget_label.itemChanged.connect(self.labelItemChanged)
        self.listwidget_label.itemDropped.connect(self.labelOrderChanged)

        self.dockwidget_label = QtWidgets.QDockWidget(self.tr("Polygon Labels"), self)
        self.dockwidget_label.setObjectName("Labels")
        self.dockwidget_label.setWidget(self.listwidget_label)

        ## uniq list widget
        self.uniqlistwidget_label = UniqueLabelQListWidget()
        self.uniqlistwidget_label.setToolTip(
            self.tr(
                "Select label to start annotating for it. "
                "Press 'Esc' to deselect."
            )
        )
        if self._dict_config["labels"]:
            for label in self._dict_config["labels"]:
                item = self.uniqlistwidget_label.createItemFromLabel(label)
                self.uniqlistwidget_label.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqlistwidget_label.setItemLabel(item, label, rgb)
        self.dockwidget_uniqlabel = QtWidgets.QDockWidget(self.tr(u"Label List"), self)
        self.dockwidget_uniqlabel.setObjectName(u"Label List")
        self.dockwidget_uniqlabel.setWidget(self.uniqlistwidget_label)


        ## uniq list widget
        self.lineeditwidget_filesearch = QtWidgets.QLineEdit()
        self.lineeditwidget_filesearch.setPlaceholderText(self.tr("Search Filename"))
        self.lineeditwidget_filesearch.textChanged.connect(self.fileSearchChanged)

        #
        self.listwidget_filelist = QtWidgets.QListWidget()
        self.listwidget_filelist.itemSelectionChanged.connect(self.fileSelectionChanged)

        vboxlayout_filelist = QtWidgets.QVBoxLayout()
        vboxlayout_filelist.setContentsMargins(0, 0, 0, 0)
        vboxlayout_filelist.setSpacing(0)
        vboxlayout_filelist.addWidget(self.lineeditwidget_filesearch)
        vboxlayout_filelist.addWidget(self.listwidget_filelist)

        widget_filelist = QtWidgets.QWidget()
        widget_filelist.setLayout(vboxlayout_filelist)

        self.dockwidget_file = QtWidgets.QDockWidget(self.tr(u"File List"), self)
        self.dockwidget_file.setObjectName(u"Files")
        self.dockwidget_file.setWidget(widget_filelist)


        self.zoomWidget = ZoomWidget()
        self.setAcceptDrops(True)

        self.canvas = self.listwidget_label.canvas = Canvas(
            epsilon=self._dict_config["epsilon"],
            double_click=self._dict_config["canvas"]["double_click"],
            num_backups=self._dict_config["canvas"]["num_backups"],
        )
        self.canvas.zoomRequest.connect(self.canvas_zoomRequest)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidget(self.canvas)
        scrollArea.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scrollArea.verticalScrollBar(),
            Qt.Horizontal: scrollArea.horizontalScrollBar(),
        }
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.canvas_newShape)
        self.canvas.shapeMoved.connect(self.canvas_shape_moved)
        self.canvas.selectionChanged.connect(self.canvas_shape_SelectionChanged)
        self.canvas.drawingPolygon.connect(self.canvas_toggle_drawingpolygon)

        self.setCentralWidget(scrollArea)       # 중앙에 scrollArea widget에 있고, 그 안에 canvas widget에 존재한다.

        features = QtWidgets.QDockWidget.DockWidgetFeatures()
        # for dock in ["dockwidget_digits",  "dockwidget_flag", "dockwidget_label", "dockwidget_uniqlabel", "dockwidget_file"]:
        for dock in [ "dockwidget_flag", "dockwidget_label", "dockwidget_uniqlabel", "dockwidget_file"]:
            if self._dict_config[dock]["closable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetClosable
            if self._dict_config[dock]["floatable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetFloatable
            if self._dict_config[dock]["movable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetMovable
            getattr(self, dock).setFeatures(features)
            if self._dict_config[dock]["show"] is False:
                getattr(self, dock).setVisible(False)

        # self.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget_digits)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget_flag)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget_uniqlabel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget_label)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget_file)

        #########################################################

        # Actions
        action = functools.partial(utils.newAction, self)   # QAction 'newAction' 부분함수를 만든다.
        shortcuts = self._dict_config["shortcuts"]

        quit = action(
            self.tr("&Quit"),                   # text
            self.close,                         # slot
            shortcuts["quit"],                  # shortcut
            "quit",                             # icon name
            self.tr("Quit application"),        # tip
        )
        
        open_ = action(
            self.tr("&Open"),
            self.openFile,
            shortcuts["open"],
            "open",
            self.tr("Open image or label file"),
        )
        opendir = action(
            self.tr("&Open Dir"),
            self.openDirDialog,
            shortcuts["open_dir"],
            "open",
            self.tr(u"Open Dir"),
        )
        openNextImg = action(
            self.tr("&Next Image"),
            self.openNextImg,
            shortcuts["open_next"],
            "next",
            self.tr(u"Open next (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )
        openPrevImg = action(
            self.tr("&Prev Image"),
            self.openPrevImg,
            shortcuts["open_prev"],
            "prev",
            self.tr(u"Open prev (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )
        save = action(
            self.tr("&Save"),
            self.saveFile,
            shortcuts["save"],
            "save",
            self.tr("Save labels to file"),
            enabled=False,
        )
        saveAs = action(
            self.tr("&Save As"),
            self.saveFileAs,
            shortcuts["save_as"],
            "save-as",
            self.tr("Save labels to a different file"),
            enabled=False,
        )

        deleteFile = action(
            self.tr("&Delete File"),
            self.deleteFile,
            shortcuts["delete_file"],
            "delete",
            self.tr("Delete current label file"),
            enabled=False,
        )

        changeOutputDir = action(
            self.tr("&Change Output Dir"),
            slot=self.changeOutputDirDialog,
            shortcut=shortcuts["save_to"],
            icon="open",
            tip=self.tr(u"Change where annotations are loaded/saved"),
        )

        saveAuto = action(
            text=self.tr("Save &Automatically"),
            slot=lambda x: self.struct_actions.saveAuto.setChecked(x),
            icon="save",
            tip=self.tr("Save automatically"),
            checkable=True,
            enabled=True,
        )
        saveAuto.setChecked(self._dict_config["auto_save"])

        saveWithImageData = action(
            text="Save With Image Data",
            slot=self.enableSaveImageWithData,
            tip="Save image data in label file",
            checkable=True,
            checked=self._dict_config["store_data"],
        )

        close = action(
            "&Close",
            self.closeFile,
            shortcuts["close"],
            "close",
            "Close current file",
        )

        toggle_keep_prev_mode = action(
            self.tr("Keep Previous Annotation"),
            self.toggleKeepPrevMode,
            shortcuts["toggle_keep_prev_mode"],
            None,
            self.tr('Toggle "keep pevious annotation" mode'),
            checkable=True,
        )

        toggle_keep_prev_mode.setChecked(self._dict_config["keep_prev"])

        createPolygonMode = action(
            self.tr("Create Polygons"),
            lambda: self.toggleDrawMode(False, createMode="polygon"),
            shortcuts["create_polygon"],
            "objects",
            self.tr("Start drawing polygons"),
            enabled=False,
        )
        createRectangleMode = action(
            self.tr("Create Rectangle"),
            lambda: self.toggleDrawMode(False, createMode="rectangle"),
            shortcuts["create_rectangle"],
            "objects",
            self.tr("Start drawing rectangles"),
            enabled=False,
        )
        createCircleMode = action(
            self.tr("Create Circle"),
            lambda: self.toggleDrawMode(False, createMode="circle"),
            shortcuts["create_circle"],
            "objects",
            self.tr("Start drawing circles"),
            enabled=False,
        )
        createLineMode = action(
            self.tr("Create Line"),
            lambda: self.toggleDrawMode(False, createMode="line"),
            shortcuts["create_line"],
            "objects",
            self.tr("Start drawing lines"),
            enabled=False,
        )
        createPointMode = action(
            self.tr("Create Point"),
            lambda: self.toggleDrawMode(False, createMode="point"),
            shortcuts["create_point"],
            "objects",
            self.tr("Start drawing points"),
            enabled=False,
        )
        createLineStripMode = action(
            self.tr("Create LineStrip"),
            lambda: self.toggleDrawMode(False, createMode="linestrip"),
            shortcuts["create_linestrip"],
            "objects",
            self.tr("Start drawing linestrip. Ctrl+LeftClick ends creation."),
            enabled=False,
        )

        editPolygonMode = action(
            self.tr("Edit Polygons"),
            self.setEditMode,
            shortcuts["edit_polygon"],
            "edit",
            self.tr("Move and edit the selected polygons"),
            enabled=False,
        )

        delete = action(
            self.tr("Delete Polygons"),
            self.deleteSelectedShape,
            shortcuts["delete_polygon"],
            "cancel",
            self.tr("Delete the selected polygons"),
            enabled=False,
        )
        copy = action(
            self.tr("Copy Polygons"),
            self.copySelectedShape,
            shortcuts["duplicate_polygon"],
            "copy",
            self.tr("Create a duplicate of the selected polygons"),
            enabled=False,
        )
        undoLastPoint = action(
            self.tr("Undo last point"),
            self.canvas.undoLastPoint,
            shortcuts["undo_last_point"],
            "undo",
            self.tr("Undo last drawn point"),
            enabled=False,
        )
        addPointToEdge = action(
            text=self.tr("Add Point to Edge"),
            slot=self.canvas.addPointToEdge,
            shortcut=shortcuts["add_point_to_edge"],
            icon="edit",
            tip=self.tr("Add point to the nearest edge"),
            enabled=False,
        )
        removePoint = action(
            text="Remove Selected Point",
            slot=self.removeSelectedPoint,
            icon="edit",
            tip="Remove selected point from polygon",
            enabled=False,
        )

        undo = action(
            self.tr("Undo"),
            self.undoShapeEdit,
            shortcuts["undo"],
            "undo",
            self.tr("Undo last add and edit of shape"),
            enabled=False,
        )

        hideAll = action(
            self.tr("&Hide\nPolygons"),
            functools.partial(self.togglePolygons, False),
            icon="eye",
            tip=self.tr("Hide all polygons"),
            enabled=False,
        )
        showAll = action(
            self.tr("&Show\nPolygons"),
            functools.partial(self.togglePolygons, True),
            icon="eye",
            tip=self.tr("Show all polygons"),
            enabled=False,
        )

        help = action(
            self.tr("&Tutorial"),
            self.tutorial,
            icon="help",
            tip=self.tr("Show tutorial page"),
        )

        zoom = QtWidgets.QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            self.tr(
                "Zoom in or out of the image. Also accessible with "
                "{} and {} from the canvas."
            ).format(
                utils.fmtShortcut(
                    "{},{}".format(shortcuts["zoom_in"], shortcuts["zoom_out"])
                ),
                utils.fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        self.zoomWidget.setEnabled(False)

        zoomIn = action(
            self.tr("Zoom &In"),
            functools.partial(self.addZoom, 1.1),
            shortcuts["zoom_in"],
            "zoom-in",
            self.tr("Increase zoom level"),
            enabled=False,
        )
        zoomOut = action(
            self.tr("&Zoom Out"),
            functools.partial(self.addZoom, 0.9),
            shortcuts["zoom_out"],
            "zoom-out",
            self.tr("Decrease zoom level"),
            enabled=False,
        )
        zoomOrg = action(
            self.tr("&Original size"),
            functools.partial(self.setZoom, 100),
            shortcuts["zoom_to_original"],
            "zoom",
            self.tr("Zoom to original size"),
            enabled=False,
        )
        fitWindow = action(
            self.tr("&Fit Window"),
            self.setFitWindow,
            shortcuts["fit_window"],
            "fit-window",
            self.tr("Zoom follows window size"),
            checkable=True,
            enabled=False,
        )
        fitWidth = action(
            self.tr("Fit &Width"),
            self.setFitWidth,
            shortcuts["fit_width"],
            "fit-width",
            self.tr("Zoom follows window width"),
            checkable=True,
            enabled=False,
        )
        brightnessContrast = action(
            "&Brightness Contrast",
            self.brightnessContrast,
            None,
            "color",
            "Adjust brightness and contrast",
            enabled=False,
        )
        #############################################################################################################
        # add a scale, rotate function

        rotate_right = action(
            "Rotate right",
            self.shape_rotate_right,
            None,
            "rotate-right",
            "rotate shape right",
            enabled=True,
        )

        rotate_left = action(
            "Rotate left",
            self.shape_rotate_left,
            None,
            "rotate-left",
            "rotate shape left",
            enabled=True,
        )

        scale_up = action(
            "scale up",
            self.shape_scale_up,
            None,
            "scale-up",
            "scale shape up",
            enabled=True,
        )

        scale_down = action(
            "scale down",
            self.shape_scale_down,
            None,
            "scale-down",
            "scale shape down",
            enabled=True,
        )

        copy_shape = action(
            "copy shape",
            self.copy_shape,
            shortcuts["copy_shape"],
            None,
            "scale shape down",
            enabled=True,
        )

        paste_shape = action(
            "paste shape",
            self.paste_shape,
            shortcuts["paste_shape"],
            None,
            "paste shape",
            enabled=True,
        )

        expand_x = action(
            "extend X",
            self.expand_x,
            None,
            'expand-x',
            "extend x",
            enabled=True,
        )

        expand_y = action(
            "expand Y",
            self.expand_y,
            None,
            'expand-y',
            "expand y",
            enabled=True,
        )


        #############################################################################################################
        # Group zoom controls into a list for easier toggling.
        zoomActions = (
            self.zoomWidget,
            zoomIn,
            zoomOut,
            zoomOrg,
            fitWindow,
            fitWidth,
        )
        self.zoomMode = self.FIT_WINDOW
        fitWindow.setChecked(Qt.Checked)
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action(
            self.tr("&Edit Label"),
            self.editLabel,
            shortcuts["edit_label"],
            "edit",
            self.tr("Modify the label of the selected polygon"),
            enabled=False,
        )

        fill_drawing = action(
            self.tr("Fill Drawing Polygon"),
            self.canvas.setFillDrawing,
            None,
            "color",
            self.tr("Fill polygon while drawing"),
            checkable=True,
            enabled=True,
        )
        fill_drawing.trigger()

        # Lavel list context menu.
        labelMenu = QtWidgets.QMenu()
        utils.addActions(labelMenu, (edit, delete))
        self.listwidget_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listwidget_label.customContextMenuRequested.connect(self.popLabelListMenu)

        # actions이라는 class에  attribute type으로  class item을 저장한다.  --> 추후 사용하기 위해 .
        self.struct_actions = utils.struct(                # class 의 변수 dict type으로 저장만 한다.
            saveAuto=saveAuto,
            saveWithImageData=saveWithImageData,
            changeOutputDir=changeOutputDir,
            save=save,
            saveAs=saveAs,
            open=open_,
            close=close,
            deleteFile=deleteFile,
            toggleKeepPrevMode=toggle_keep_prev_mode,
            delete=delete,
            edit=edit,
            copy=copy,
            undoLastPoint=undoLastPoint,
            undo=undo,
            addPointToEdge=addPointToEdge,
            removePoint=removePoint,
            createPolygonMode=createPolygonMode,
            editMode=editPolygonMode,
            createRectangleMode=createRectangleMode,
            createCircleMode=createCircleMode,
            createLineMode=createLineMode,
            createPointMode=createPointMode,
            createLineStripMode=createLineStripMode,

            zoom=zoom,
            zoomIn=zoomIn,
            zoomOut=zoomOut,
            zoomOrg=zoomOrg,
            fitWindow=fitWindow,
            fitWidth=fitWidth,
            brightnessContrast=brightnessContrast,
            zoomActions=zoomActions,
            openNextImg=openNextImg,
            openPrevImg=openPrevImg,
            rotate_right=rotate_right,
            rotate_left=rotate_left,
            scale_up=scale_up,
            scale_down=scale_down,
            copy_shape=copy_shape,
            paste_shape=paste_shape,
            expand_x=expand_x,
            expand_y=expand_y,
            fileMenuActions=(open_, opendir, save, saveAs, close, quit),
            tool=(),       # 왼쪽 toolbar을 만들 때, 필요한 action을 만든다.
            # Edit menu 밑에  추가되는 메뉴. 아래에 있는  menu 다음에  editMenu가 추가적으로 붙는다.
            editMenu=(
                edit,
                copy,
                delete,
                None,
                undo,
                undoLastPoint,
                None,
                addPointToEdge,
                None,
                toggle_keep_prev_mode,
                copy_shape,
                paste_shape,
            ),
            # menu shown at right click이거도 하지만,   Edit Menu에 추가되는 메뉴이기도 함.
            menu_canvas=(
                createPolygonMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                editPolygonMode,
                edit,
                copy,
                delete,
                undo,
                undoLastPoint,
                addPointToEdge,
                removePoint,
                copy_shape,
                paste_shape,
            ),
            onLoadActive=(
                close,
                createPolygonMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                editPolygonMode,
                brightnessContrast,
            ),
            onShapesPresent=(saveAs, hideAll, showAll),
        )

        self.canvas.edgeSelected.connect(self.canvas_shape_edge_selected)
        self.canvas.vertexSelected.connect(self.struct_actions.removePoint.setEnabled)

        ###################################################################################################
        #  head linebar menu
        self.struct_head_menus = utils.struct(                  # struct class을 만들어,  menus에 저장한다.
            file=self.menu(self.tr("&File")),       # menubar을 만들어 return하고,  'file' attribute에 저장한다.
            edit=self.menu(self.tr("&Edit")),
            view=self.menu(self.tr("&View")),
            help=self.menu(self.tr("&Help")),
            recentFiles=QtWidgets.QMenu(self.tr("Open &Recent")),
            labelList=labelMenu,
        )

        utils.addActions(
            self.struct_head_menus.file,
            (
                open_,
                openNextImg,
                openPrevImg,
                opendir,
                self.struct_head_menus.recentFiles,
                save,
                saveAs,
                saveAuto,
                changeOutputDir,
                saveWithImageData,
                close,
                deleteFile,
                None,
                quit,
            ),
        )
        utils.addActions(self.struct_head_menus.help, (help,))
        utils.addActions(
            self.struct_head_menus.view,
            (
                self.dockwidget_flag.toggleViewAction(),
                self.dockwidget_uniqlabel.toggleViewAction(),
                self.dockwidget_label.toggleViewAction(),
                self.dockwidget_file.toggleViewAction(),
                None,
                fill_drawing,
                None,
                hideAll,
                showAll,
                None,
                zoomIn,
                zoomOut,
                zoomOrg,
                None,
                fitWindow,
                fitWidth,
                None,
                brightnessContrast,
            ),
        )

        self.struct_head_menus.file.aboutToShow.connect(self.updateFileMenu)

        #######################################################################################################
        # labelme canvas 에는 2개의  menu가 있다.
        utils.addActions(self.canvas.menus[0], self.struct_actions.menu_canvas)     # 0: right-click without selection and dragging of shapes
        utils.addActions(                                                           # 1: right-click with selection and dragging of shapes
            self.canvas.menus[1],
            (
                action("&Copy here", self.copyShape),
                action("&Move here", self.moveShape),
            ),
        )

        #######################################################################################################
        self.toolbar = self.make_toolbar("Tools")      # 화면의 왼쪽에 toolbar을 만든다
        # Menu buttons on Left, 화면의 왼쪽 toolbar에 존재하는 menu들 . self.populateModeActions()에서  수행된다.
        self.struct_actions.menu_toolbar = (
            # open_,
            opendir,
            openNextImg,
            openPrevImg,
            # save,
            # deleteFile,
            None,               # 메뉴 seperator이다
            createPolygonMode,
            editPolygonMode,
            copy,
            # delete,
            undo,
            # brightnessContrast,
            None,
            zoom,
            fitWidth,
            None,
            rotate_right,
            rotate_left,
            scale_up,
            scale_down,
            expand_x,
            expand_y,
        )

        #######################################################################################################
        self.statusBar().showMessage(self.tr("%s started.") % __appname__)
        self.statusBar().show()

        #######################################################################################################
        if output_file is not None and self._dict_config["auto_save"]:
            logger.warn(
                "If `auto_save` argument is True, `output_file` argument "
                "is ignored and output filename is automatically "
                "set as IMAGE_BASENAME.json."
            )
        self.output_file = output_file
        self.output_dir = output_dir

        # Application state.
        self.image = QtGui.QImage()
        self.imagePath = None
        self.list_recentFiles = []
        self.maxRecent = 7
        self.otherData = None
        self.zoom_level = 100
        self.fit_window = False
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value)
        self.brightnessContrast_values = {}
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value

        if filename is not None and osp.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        if dict_config["file_search"]:
            self.lineeditwidget_filesearch.setText(dict_config["file_search"])
            self.fileSearchChanged()

        # XXX: Could be completely declarative.
        # Restore application settings.
        self.settings = QtCore.QSettings("labelme", "labelme")
        # FIXME: QSettings.value can return None on PyQt4
        self.list_recentFiles = self.settings.value("recentFiles", []) or []
        size = self.settings.value("window/size", QtCore.QSize(600, 500))
        position = self.settings.value("window/position", QtCore.QPoint(0, 0))
        self.resize(size)
        self.move(position)
        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState( self.settings.value("window/state", QtCore.QByteArray()) )

        # Populate the File menu dynamically.
        self.updateFileMenu()
        # Since loading the file may take some time,
        # make sure it runs in the background.
        if self.filename is not None:
            self.queueEvent(functools.partial(self.loadFile, self.filename))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # self.firstStart = True
        # if self.firstStart:
        #    QWhatsThis.enterWhatsThisMode()

    def menu(self, title, actions=None):        # 새로운 menubar을 만들어 return한다
        menu = self.menuBar().addMenu(title)
        if actions:
            utils.addActions(menu, actions)
        return menu

    def make_toolbar(self, title, actions=None):
        toolbar = ToolBar(title)            # toolbar class을 만들어 반환한다.
        toolbar.setObjectName("%sToolBar" % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            utils.addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)            # 방금 생성한 toolbar을  화면의 왼쪽에  위치시킨다.
        return toolbar

    # Support Functions

    def noShapes(self):
        return not len(self.listwidget_label)

    def populateModeActions(self):
        '''
        여기서는  메뉴들을 추가 조정한다.
        self.tools <- tool
        self.canvas.menus <- menu
        self.menus.edit <- actions + self.actions.editMenu
        '''
        tool, menu = self.struct_actions.menu_toolbar, self.struct_actions.menu_canvas
        self.toolbar.clear()
        utils.addActions(self.toolbar, tool)
        self.canvas.menus[0].clear()
        utils.addActions(self.canvas.menus[0], menu)
        self.struct_head_menus.edit.clear()
        actions = (
            self.struct_actions.createPolygonMode,
            self.struct_actions.createRectangleMode,
            self.struct_actions.createCircleMode,
            self.struct_actions.createLineMode,
            self.struct_actions.createPointMode,
            self.struct_actions.createLineStripMode,
            self.struct_actions.editMode,
        )
        utils.addActions(self.struct_head_menus.edit, actions + self.struct_actions.editMenu)

    def canvas_shape_moved(self):
        # listwidget_flag 에서 item 이 변화면 call 된다.
        self.struct_actions.undo.setEnabled(self.canvas.isShapeRestorable)

        if self._dict_config["auto_save"] or self.struct_actions.saveAuto.isChecked():
            label_file = osp.splitext(self.imagePath)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            self.saveLabels(label_file)
            return
        self.dirty = True
        self.struct_actions.save.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}*".format(title, self.filename)
        self.setWindowTitle(title)

    def setClean(self):
        self.dirty = False
        self.struct_actions.save.setEnabled(False)
        self.struct_actions.createPolygonMode.setEnabled(True)
        self.struct_actions.createRectangleMode.setEnabled(True)
        self.struct_actions.createCircleMode.setEnabled(True)
        self.struct_actions.createLineMode.setEnabled(True)
        self.struct_actions.createPointMode.setEnabled(True)
        self.struct_actions.createLineStripMode.setEnabled(True)
        self.struct_actions.expand_x.setEnabled(True)
        self.struct_actions.expand_y.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}".format(title, self.filename)
        self.setWindowTitle(title)

        if self.hasLabelFile():
            self.struct_actions.deleteFile.setEnabled(True)
        else:
            self.struct_actions.deleteFile.setEnabled(False)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.struct_actions.zoomActions:
            z.setEnabled(value)
        for action in self.struct_actions.onLoadActive:
            action.setEnabled(value)

    def canvas_shape_edge_selected(self, selected, shape):
        self.struct_actions.addPointToEdge.setEnabled(
            selected and shape and shape.canAddPoint()
        )

    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.listwidget_label.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

    def currentItem(self):
        items = self.listwidget_label.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filename):
        if filename in self.list_recentFiles:
            self.list_recentFiles.remove(filename)
        elif len(self.list_recentFiles) >= self.maxRecent:
            self.list_recentFiles.pop()
        self.list_recentFiles.insert(0, filename)

    # Callbacks

    def undoShapeEdit(self):
        self.canvas.restoreShape()
        self.listwidget_label.clear()
        self.loadShapes(self.canvas.shapes)
        self.struct_actions.undo.setEnabled(self.canvas.isShapeRestorable)

    def tutorial(self):
        url = "https://github.com/wkentaro/labelme/tree/master/examples/tutorial"  # NOQA
        webbrowser.open(url)

    def canvas_toggle_drawingpolygon(self, drawing=True):
        """Toggle drawing sensitive.

        In the middle of drawing, toggling between modes should be disabled.
        """
        self.struct_actions.editMode.setEnabled(not drawing)
        self.struct_actions.undoLastPoint.setEnabled(drawing)
        self.struct_actions.undo.setEnabled(not drawing)
        self.struct_actions.delete.setEnabled(not drawing)

    def toggleDrawMode(self, edit=True, createMode="polygon"):
        self.canvas.setEditing(edit)
        self.canvas.createMode = createMode
        if edit:
            self.struct_actions.createPolygonMode.setEnabled(True)
            self.struct_actions.createRectangleMode.setEnabled(True)
            self.struct_actions.createCircleMode.setEnabled(True)
            self.struct_actions.createLineMode.setEnabled(True)
            self.struct_actions.createPointMode.setEnabled(True)
            self.struct_actions.createLineStripMode.setEnabled(True)
            self.struct_actions.expand_x.setEnabled(True)
            self.struct_actions.expand_y.setEnabled(True)

        else:
            if createMode == "polygon":
                self.struct_actions.createPolygonMode.setEnabled(False)
                self.struct_actions.createRectangleMode.setEnabled(True)
                self.struct_actions.createCircleMode.setEnabled(True)
                self.struct_actions.createLineMode.setEnabled(True)
                self.struct_actions.createPointMode.setEnabled(True)
                self.struct_actions.createLineStripMode.setEnabled(True)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            elif createMode == "rectangle":
                self.struct_actions.createPolygonMode.setEnabled(True)
                self.struct_actions.createRectangleMode.setEnabled(False)
                self.struct_actions.createCircleMode.setEnabled(True)
                self.struct_actions.createLineMode.setEnabled(True)
                self.struct_actions.createPointMode.setEnabled(True)
                self.struct_actions.createLineStripMode.setEnabled(True)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            elif createMode == "line":
                self.struct_actions.createPolygonMode.setEnabled(True)
                self.struct_actions.createRectangleMode.setEnabled(True)
                self.struct_actions.createCircleMode.setEnabled(True)
                self.struct_actions.createLineMode.setEnabled(False)
                self.struct_actions.createPointMode.setEnabled(True)
                self.struct_actions.createLineStripMode.setEnabled(True)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            elif createMode == "point":
                self.struct_actions.createPolygonMode.setEnabled(True)
                self.struct_actions.createRectangleMode.setEnabled(True)
                self.struct_actions.createCircleMode.setEnabled(True)
                self.struct_actions.createLineMode.setEnabled(True)
                self.struct_actions.createPointMode.setEnabled(False)
                self.struct_actions.createLineStripMode.setEnabled(True)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            elif createMode == "circle":
                self.struct_actions.createPolygonMode.setEnabled(True)
                self.struct_actions.createRectangleMode.setEnabled(True)
                self.struct_actions.createCircleMode.setEnabled(False)
                self.struct_actions.createLineMode.setEnabled(True)
                self.struct_actions.createPointMode.setEnabled(True)
                self.struct_actions.createLineStripMode.setEnabled(True)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            elif createMode == "linestrip":
                self.struct_actions.createPolygonMode.setEnabled(True)
                self.struct_actions.createRectangleMode.setEnabled(True)
                self.struct_actions.createCircleMode.setEnabled(True)
                self.struct_actions.createLineMode.setEnabled(True)
                self.struct_actions.createPointMode.setEnabled(True)
                self.struct_actions.createLineStripMode.setEnabled(False)
                self.struct_actions.expand_x.setEnabled(True)
                self.struct_actions.expand_y.setEnabled(True)

            else:
                raise ValueError("Unsupported createMode: %s" % createMode)
        self.struct_actions.editMode.setEnabled(not edit)

    def setEditMode(self):
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        current = self.filename

        def exists(filename):
            return osp.exists(str(filename))

        menu = self.struct_head_menus.recentFiles
        menu.clear()
        files = [f for f in self.list_recentFiles if f != current and exists(f)]
        for i, f in enumerate(files):
            icon = utils.newIcon("labels")
            action = QtWidgets.QAction( icon, "&%d %s" % (i + 1, QtCore.QFileInfo(f).fileName()), self )
            action.triggered.connect(functools.partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.struct_head_menus.labelList.exec_(self.listwidget_label.mapToGlobal(point))

    def validateLabel(self, label):
        # no validation
        if self._dict_config["validate_label"] is None:
            return True

        for i in range(self.uniqlistwidget_label.count()):
            label_i = self.uniqlistwidget_label.item(i).data(Qt.UserRole)
            if self._dict_config["validate_label"] in ["exact"]:
                if label_i == label:
                    return True
        return False

    def editLabel(self, item=None):
        if item and not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem type")

        if not self.canvas.editing():
            return
        if not item:
            item = self.currentItem()
        if item is None:
            return
        shape = item.shape()
        if shape is None:
            return
        text, flags, group_id = self.labelDialog.popUp(
            text=shape.label,
            flags=shape.flags,
            group_id=shape.group_id,
        )
        if text is None:
            return
        if not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._dict_config["validate_label"]
                ),
            )
            return
        shape.label = text
        shape.flags = flags
        shape.group_id = group_id
        if shape.group_id is None:
            item.setText(shape.label)
        else:
            item.setText("{} ({})".format(shape.label, shape.group_id))
        self.canvas_shape_moved()
        if not self.uniqlistwidget_label.findItemsByLabel(shape.label):
            item = QtWidgets.QListWidgetItem()
            item.setData(Qt.UserRole, shape.label)
            self.uniqlistwidget_label.addItem(item)

    def fileSearchChanged(self):
        self.importDirImages(
            self.lastOpenDir,
            pattern=self.lineeditwidget_filesearch.text(),
            load=False,
        )

    def fileSelectionChanged(self):
        items = self.listwidget_filelist.selectedItems()
        if not items:
            return
        item = items[0]

        if not self.mayContinue():
            return

        currIndex = self.imageList.index(str(item.text()))
        if currIndex < len(self.imageList):
            filename = self.imageList[currIndex]
            if filename:
                self.loadFile(filename)

    # React to canvas signals.
    def canvas_shape_SelectionChanged(self, selected_shapes):
        self._noSelectionSlot = True
        for shape in self.canvas.selectedShapes:
            shape.selected = False
        self.listwidget_label.clearSelection()
        self.canvas.selectedShapes = selected_shapes
        for shape in self.canvas.selectedShapes:
            shape.selected = True
            item = self.listwidget_label.findItemByShape(shape)
            self.listwidget_label.selectItem(item)
            self.listwidget_label.scrollToItem(item)
        self._noSelectionSlot = False
        n_selected = len(selected_shapes)
        self.struct_actions.delete.setEnabled(n_selected)
        self.struct_actions.copy.setEnabled(n_selected)
        self.struct_actions.edit.setEnabled(n_selected == 1)

        self.struct_actions.rotate_right.setEnabled(n_selected)
        self.struct_actions.rotate_left.setEnabled(n_selected)
        self.struct_actions.scale_up.setEnabled(n_selected)
        self.struct_actions.scale_down.setEnabled(n_selected)
        self.struct_actions.copy_shape.setEnabled(n_selected)
        self.struct_actions.paste_shape.setEnabled(n_selected)
        self.struct_actions.expand_x.setEnabled(n_selected)
        self.struct_actions.expand_y.setEnabled(n_selected)

    def addLabel(self, shape):
        if shape.group_id is None:
            text = shape.label
        else:
            text = "{} ({})".format(shape.label, shape.group_id)
        label_list_item = LabelListWidgetItem(text, shape)
        self.listwidget_label.addItem(label_list_item)
        if not self.uniqlistwidget_label.findItemsByLabel(shape.label):
            item = self.uniqlistwidget_label.createItemFromLabel(shape.label)
            self.uniqlistwidget_label.addItem(item)
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqlistwidget_label.setItemLabel(item, shape.label, rgb)
        self.labelDialog.addLabelHistory(shape.label)
        for action in self.struct_actions.onShapesPresent:
            action.setEnabled(True)

        rgb = self._get_rgb_by_label(shape.label)

        r, g, b = rgb
        label_list_item.setText(
            '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                text, r, g, b
            )
        )
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 128)
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 155)

    def _get_rgb_by_label(self, label):
        if self._dict_config["shape_color"] == "auto":
            item = self.uniqlistwidget_label.findItemsByLabel(label)[0]
            label_id = self.uniqlistwidget_label.indexFromItem(item).row() + 1
            label_id += self._dict_config["shift_auto_shape_color"]
            return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]
        elif (
            self._dict_config["shape_color"] == "manual"
            and self._dict_config["label_colors"]
            and label in self._dict_config["label_colors"]
        ):
            return self._dict_config["label_colors"][label]
        elif self._dict_config["default_shape_color"]:
            return self._dict_config["default_shape_color"]

    def remLabels(self, shapes):
        for shape in shapes:
            item = self.listwidget_label.findItemByShape(shape)
            self.listwidget_label.removeItem(item)

    def loadShapes(self, shapes, replace=True):
        self._noSelectionSlot = True
        for shape in shapes:
            self.addLabel(shape)
        self.listwidget_label.clearSelection()
        self._noSelectionSlot = False
        self.canvas.loadShapes(shapes, replace=replace)

    def loadLabels(self, shapes):
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            shape_type = shape["shape_type"]
            flags = shape["flags"]
            group_id = shape["group_id"]
            other_data = shape["other_data"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                shape_type=shape_type,
                group_id=group_id,
            )
            for x, y in points:
                shape.addPoint(QtCore.QPointF(x, y))
            shape.close()

            default_flags = {}
            if self._dict_config["label_flags"]:
                for pattern, keys in self._dict_config["label_flags"].items():
                    if re.match(pattern, label):
                        for key in keys:
                            default_flags[key] = False
            shape.flags = default_flags
            shape.flags.update(flags)
            shape.other_data = other_data

            s.append(shape)
        self.loadShapes(s)

    def loadFlags(self, flags):
        self.listwidget_flag.clear()
        for key, flag in flags.items():
            item = QtWidgets.QListWidgetItem(key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)
            self.listwidget_flag.addItem(item)

    def saveLabels(self, filename):
        lf = LabelFile()

        def format_shape(s):
            data = s.other_data.copy()
            data.update(
                dict(
                    label=s.label.encode("utf-8") if PY2 else s.label,
                    points=[(p.x(), p.y()) for p in s.points],
                    group_id=s.group_id,
                    shape_type=s.shape_type,
                    flags=s.flags,
                )
            )
            return data

        shapes = [format_shape(item.shape()) for item in self.listwidget_label]
        flags = {}
        for i in range(self.listwidget_flag.count()):
            item = self.listwidget_flag.item(i)
            key = item.text()
            flag = item.checkState() == Qt.Checked
            flags[key] = flag
        try:
            imagePath = osp.relpath(self.imagePath, osp.dirname(filename))      # 상대경로를 구한다.
            imageData = self.imageData if self._dict_config["store_data"] else None
            if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
            lf.save(
                filename=filename,
                shapes=shapes,
                imagePath=imagePath,
                imageData=imageData,
                imageHeight=self.image.height(),
                imageWidth=self.image.width(),
                otherData=self.otherData,
                flags=flags,
            )
            self.labelFile = lf
            items = self.listwidget_filelist.findItems( self.imagePath, Qt.MatchExactly )
            if len(items) > 0:
                if len(items) != 1:
                    raise RuntimeError("There are duplicate files.")
                items[0].setCheckState(Qt.Checked)
            # disable allows next and previous image to proceed
            # self.filename = filename
            return True
        except LabelFileError as e:
            self.errorMessage( self.tr("Error saving label data"), self.tr("<b>%s</b>") % e )
            return False

    def copySelectedShape(self):
        added_shapes = self.canvas.copySelectedShapes()
        self.listwidget_label.clearSelection()
        for shape in added_shapes:
            self.addLabel(shape)
        self.canvas_shape_moved()

    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.canvas.editing():
            selected_shapes = []
            for item in self.listwidget_label.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.canvas.selectShapes(selected_shapes)
            else:
                self.canvas.deSelectShape()

    def labelItemChanged(self, item):
        shape = item.shape()
        self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.canvas_shape_moved()
        self.canvas.loadShapes([item.shape() for item in self.listwidget_label])

    # Callback functions:

    def canvas_newShape(self):
        """ canvas에서 새로운 shape이 생기면  call된다.

        position MUST be in global coordinates.
        """
        items = self.uniqlistwidget_label.selectedItems()
        text = None
        if items:
            text = items[0].data(Qt.UserRole)
        flags = {}
        group_id = None
        if self._dict_config["display_label_popup"] or not text:
            previous_text = self.labelDialog.edit.text()
            text, flags, group_id = self.labelDialog.popUp(text)
            if not text:
                self.labelDialog.edit.setText(previous_text)

        if text and not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._dict_config["validate_label"]
                ),
            )
            text = ""
        if text:
            self.listwidget_label.clearSelection()
            shape = self.canvas.setLastLabel(text, flags)
            shape.group_id = group_id
            self.addLabel(shape)
            self.struct_actions.editMode.setEnabled(True)
            self.struct_actions.undoLastPoint.setEnabled(False)
            self.struct_actions.undo.setEnabled(True)
            self.canvas_shape_moved()
        else:
            self.canvas.undoLastLine()
            self.canvas.shapesBackups.pop()

    def scrollRequest(self, delta, orientation):
        units = -delta * 0.1  # natural scroll
        bar = self.scrollBars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)

    def setScroll(self, orientation, value):
        self.scrollBars[orientation].setValue(value)
        self.scroll_values[orientation][self.filename] = value

    def setZoom(self, value):
        self.struct_actions.fitWidth.setChecked(False)
        self.struct_actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def addZoom(self, increment=1.1):
        zoom_value = self.zoomWidget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)
        else:
            zoom_value = math.floor(zoom_value)
        self.setZoom(zoom_value)

    def canvas_zoomRequest(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.addZoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.scrollBars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.scrollBars[Qt.Vertical].value() + y_shift,
            )

    def setFitWindow(self, value=True):
        if value:
            self.struct_actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.struct_actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def onNewBrightnessContrast(self, qimage):
        self.canvas.loadPixmap(
            QtGui.QPixmap.fromImage(qimage), clear_shapes=False
        )

    def brightnessContrast(self, value):
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        dialog.exec_()

        brightness = dialog.slider_brightness.value()
        contrast = dialog.slider_contrast.value()
        self.brightnessContrast_values[self.filename] = (brightness, contrast)

    def togglePolygons(self, value):
        for item in self.listwidget_label:
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def loadFile(self, filename=None):
        """Load the specified file, or the last opened file if None."""
        # changing fileListWidget loads file
        if filename in self.imageList and ( self.listwidget_filelist.currentRow() != self.imageList.index(filename) ):
            self.listwidget_filelist.setCurrentRow(self.imageList.index(filename))
            self.listwidget_filelist.repaint()
            return

        self.resetState()
        self.canvas.setEnabled(False)
        if filename is None:
            filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("No such file: <b>%s</b>") % filename,
            )
            return False
        # assumes same name, but json extension
        self.status(self.tr("Loading %s...") % osp.basename(str(filename)))
        label_file = osp.splitext(filename)[0] + ".json"
        if self.output_dir:
            label_file_without_path = osp.basename(label_file)
            label_file = osp.join(self.output_dir, label_file_without_path)
        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file( label_file ):
            try:
                self.labelFile = LabelFile(label_file)
            except LabelFileError as e:
                self.errorMessage(
                    self.tr("Error opening file"),
                    self.tr(
                        "<p><b>%s</b></p>"
                        "<p>Make sure <i>%s</i> is a valid label file."
                    )
                    % (e, label_file),
                )
                self.status(self.tr("Error reading %s") % label_file)
                return False
            self.imageData = self.labelFile.imageData
            self.imagePath = osp.join( osp.dirname(label_file), self.labelFile.imagePath, )
            self.otherData = self.labelFile.otherData
        else:
            self.imageData = LabelFile.load_image_file(filename)
            if self.imageData:
                self.imagePath = filename
            self.labelFile = None
        image = QtGui.QImage.fromData(self.imageData)

        if image.isNull():
            formats = [
                "*.{}".format(fmt.data().decode())
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr(
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, ",".join(formats)),
            )
            self.status(self.tr("Error reading %s") % filename)
            return False
        self.image = image
        self.filename = filename
        if self._dict_config["keep_prev"]:
            prev_shapes = self.canvas.shapes
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))
        flags = {k: False for k in self._dict_config["flags"] or []}
        if self.labelFile:
            self.loadLabels(self.labelFile.shapes)
            if self.labelFile.flags is not None:
                flags.update(self.labelFile.flags)
        self.loadFlags(flags)
        if self._dict_config["keep_prev"] and self.noShapes():
            self.loadShapes(prev_shapes, replace=False)
            self.canvas_shape_moved()
        else:
            self.setClean()
        self.canvas.setEnabled(True)
        # set zoom values
        is_initial_load = not self.zoom_values
        if self.filename in self.zoom_values:
            self.zoomMode = self.zoom_values[self.filename][0]
            self.setZoom(self.zoom_values[self.filename][1])
        elif is_initial_load or not self._dict_config["keep_prev_scale"]:
            self.adjustScale(initial=True)
        # set scroll values
        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.setScroll( orientation, self.scroll_values[orientation][self.filename] )
        # set brightness constrast values
        dialog = BrightnessContrastDialog( utils.img_data_to_pil(self.imageData), self.onNewBrightnessContrast, parent=self, )
        brightness, contrast = self.brightnessContrast_values.get( self.filename, (None, None) )
        if self._dict_config["keep_prev_brightness"] and self.list_recentFiles:
            brightness, _ = self.brightnessContrast_values.get( self.list_recentFiles[0], (None, None) )
        if self._dict_config["keep_prev_contrast"] and self.list_recentFiles:
            _, contrast = self.brightnessContrast_values.get( self.list_recentFiles[0], (None, None) )
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        self.brightnessContrast_values[self.filename] = (brightness, contrast)
        if brightness is not None or contrast is not None:
            dialog.onNewValue(None)
        self.paintCanvas()
        self.addRecentFile(self.filename)
        self.toggleActions(True)
        self.canvas.setFocus()
        currIndex = self.imageList.index(self.filename)

        self.status(self.tr("Loaded %s : %d/%d") % (osp.basename(str(filename)), currIndex, len(self.imageList) ))
        return True

    def resizeEvent(self, event):
        if (
            self.canvas
            and not self.image.isNull()
            and self.zoomMode != self.MANUAL_ZOOM
        ):
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        value = int(100 * value)
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def scaleFitWindow(self):
        """Figure out the size of the pixmap to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def enableSaveImageWithData(self, enabled):
        self._dict_config["store_data"] = enabled
        self.struct_actions.saveWithImageData.setChecked(enabled)

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        self.settings.setValue( "filename", self.filename if self.filename else "" )
        self.settings.setValue("window/size", self.size())
        self.settings.setValue("window/position", self.pos())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("recentFiles", self.list_recentFiles)
        # ask the use for where to save the labels
        # self.settings.setValue('window/geometry', self.saveGeometry())

    def dragEnterEvent(self, event):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        if event.mimeData().hasUrls():
            items = [i.toLocalFile() for i in event.mimeData().urls()]
            if any([i.lower().endswith(tuple(extensions)) for i in items]):
                event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self.mayContinue():
            event.ignore()
            return
        items = [i.toLocalFile() for i in event.mimeData().urls()]
        self.importDroppedImageFiles(items)

    # User Dialogs #

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def openPrevImg(self, _value=False):
        keep_prev = self._dict_config["keep_prev"]
        if Qt.KeyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self._dict_config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        if self.filename is None:
            return

        currIndex = self.imageList.index(self.filename)
        if currIndex - 1 >= 0:
            filename = self.imageList[currIndex - 1]
            if filename:
                self.loadFile(filename)

        self._dict_config["keep_prev"] = keep_prev

    def openNextImg(self, _value=False, load=True):
        keep_prev = self._dict_config["keep_prev"]
        if Qt.KeyboardModifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self._dict_config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        filename = None
        if self.filename is None:
            filename = self.imageList[0]
        else:
            currIndex = self.imageList.index(self.filename)
            if currIndex + 1 < len(self.imageList):
                filename = self.imageList[currIndex + 1]
            else:
                filename = self.imageList[-1]
        self.filename = filename

        if self.filename and load:
            self.loadFile(self.filename)

        self._dict_config["keep_prev"] = keep_prev

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = osp.dirname(str(self.filename)) if self.filename else "."
        formats = [
            "*.{}".format(fmt.data().decode())
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        filters = self.tr("Image & Label files (%s)") % " ".join(
            formats + ["*%s" % LabelFile.suffix]
        )
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Image or Label file") % __appname__,
            path,
            filters,
        )
        if QT5:
            filename, _ = filename
        filename = str(filename)
        if filename:
            self.loadFile(filename)

    def changeOutputDirDialog(self, _value=False):
        default_output_dir = self.output_dir
        if default_output_dir is None and self.filename:
            default_output_dir = osp.dirname(self.filename)
        if default_output_dir is None:
            default_output_dir = self.currentPath()

        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("%s - Save/Load Annotations in Directory") % __appname__,
            default_output_dir,
            QtWidgets.QFileDialog.ShowDirsOnly
            | QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        output_dir = str(output_dir)

        if not output_dir:
            return

        self.output_dir = output_dir

        self.statusBar().showMessage( self.tr("%s . Annotations will be saved/loaded in %s") % ("Change Annotations Dir", self.output_dir) )
        self.statusBar().show()

        current_filename = self.filename
        self.importDirImages(self.lastOpenDir, load=False)

        if current_filename in self.imageList:
            # retain currently selected file
            self.listwidget_filelist.setCurrentRow( self.imageList.index(current_filename) )
            self.listwidget_filelist.repaint()

    def saveFile(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        if self.labelFile:
            # DL20180323 - overwrite when in directory
            self._saveFile(self.labelFile.filename)
        elif self.output_file:
            self._saveFile(self.output_file)
            self.close()
        else:
            self._saveFile(self.saveFileDialog())

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = self.tr("%s - Choose File") % __appname__
        filters = self.tr("Label files (*%s)") % LabelFile.suffix
        if self.output_dir:
            dlg = QtWidgets.QFileDialog( self, caption, self.output_dir, filters )
        else:
            dlg = QtWidgets.QFileDialog( self, caption, self.currentPath(), filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)
        basename = osp.basename(osp.splitext(self.filename)[0])
        if self.output_dir:
            default_labelfile_name = osp.join( self.output_dir, basename + LabelFile.suffix )
        else:
            default_labelfile_name = osp.join( self.currentPath(), basename + LabelFile.suffix)

        # default으로  default_labelfile_name 을 사용한다. 그러므로, dlg은 필요하지 않다.
        ##filename = dlg.getSaveFileName( self, self.tr("Choose File"), default_labelfile_name, self.tr("Label files (*%s)") % LabelFile.suffix,)

        filename = default_labelfile_name
        if isinstance(filename, tuple):
            filename, _ = filename
        return filename

    def shape_rotate_right(self):
        degree = 10
        if QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier :
            degree = 1

        self.canvas.rotateShape(degree)


    def shape_rotate_left(self):
        degree = -10
        if QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier :
            degree = -1

        self.canvas.rotateShape(degree)

    def shape_scale_up(self):
        scale_f = 1.1
        if QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier :
            scale_f = 1.02

        self.canvas.scaleShape(scale_f)

    def shape_scale_down(self):
        scale_f = 0.9
        if QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier :
            scale_f = 0.98

        self.canvas.scaleShape(scale_f)

    def copy_shape(self):
        self.copied_shapes = self.canvas.copySelectedShapes(copy_only=True)
        if len(self.copied_shapes) > 0 :
            self.status('shapes was copied')
        else:
            self.status('No selection, Not copied')

    def paste_shape(self):
        if  hasattr(self, 'copied_shapes') and   len(self.copied_shapes) > 0:
            self.listwidget_label.clearSelection()
            for shape in self.copied_shapes:
                self.addLabel(shape)
            self.canvas.loadShapes(self.copied_shapes, replace=False)
            self.canvas_shape_moved()
            self.status('Shape was pasted.')

    def expand_x(self):
        scale_f = 1.1
        if QtWidgets.QApplication.keyboardModifiers() == Qt.AltModifier:
            scale_f = 0.98
        elif QtWidgets.QApplication.keyboardModifiers() == Qt.ShiftModifier:
            scale_f = 0.9
        elif QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier:
            scale_f = 1.01

        self.canvas.expand_axis(scale_f, axis=0)

    def expand_y(self):
        scale_f = 1.1
        if QtWidgets.QApplication.keyboardModifiers() == Qt.AltModifier:
            scale_f = 0.98
        elif QtWidgets.QApplication.keyboardModifiers() == Qt.ShiftModifier:
            scale_f = 0.9
        elif QtWidgets.QApplication.keyboardModifiers() == Qt.ControlModifier:
            scale_f = 1.01

        self.canvas.expand_axis(scale_f, axis=1)


    def _saveFile(self, filename):
        if filename and self.saveLabels(filename):
            self.addRecentFile(filename)
            self.setClean()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.struct_actions.saveAs.setEnabled(False)

    def getLabelFile(self):
        if self.filename.lower().endswith(".json"):
            label_file = self.filename
        else:
            label_file = osp.splitext(self.filename)[0] + ".json"

        return label_file

    def deleteFile(self):
        mb = QtWidgets.QMessageBox
        msg = self.tr(
            "You are about to permanently delete this label file, "
            "proceed anyway?"
        )
        answer = mb.warning(self, self.tr("Attention"), msg, mb.Yes | mb.No)
        if answer != mb.Yes:
            return

        label_file = self.getLabelFile()
        if osp.exists(label_file):
            os.remove(label_file)
            logger.info("Label file is removed: {}".format(label_file))

            item = self.listwidget_filelist.currentItem()
            item.setCheckState(Qt.Unchecked)

            self.resetState()

    # Message Dialogs. #
    def hasLabels(self):
        if self.noShapes():
            self.errorMessage( "No objects labeled", "You must label at least one object to save the file.",)
            return False
        return True

    def hasLabelFile(self):
        if self.filename is None:
            return False

        label_file = self.getLabelFile()
        return osp.exists(label_file)

    def mayContinue(self):
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = self.tr('Save annotations to "{}" before closing?').format( self.filename)
        # answer = mb.question(
        #     self,
        #     self.tr("Save annotations?"),
        #     msg,
        #     mb.Save | mb.Discard | mb.Cancel,
        #     mb.Save,
        # )
        answer = mb.Save
        if answer == mb.Discard:
            return True
        elif answer == mb.Save:
            self.saveFile()
            return True
        else:  # answer == mb.Cancel
            return False

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical( self, title, "<p><b>%s</b></p>%s" % (title, message) )

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    def toggleKeepPrevMode(self):
        self._dict_config["keep_prev"] = not self._dict_config["keep_prev"]

    def removeSelectedPoint(self):
        self.canvas.removeSelectedPoint()
        if not self.canvas.hShape.points:
            self.canvas.deleteShape(self.canvas.hShape)
            self.remLabels([self.canvas.hShape])
            self.canvas_shape_moved()
            if self.noShapes():
                for action in self.struct_actions.onShapesPresent:
                    action.setEnabled(False)

    def deleteSelectedShape(self):
        yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        msg = self.tr("You are about to permanently delete {} polygons, " "proceed anyway?" ).format(len(self.canvas.selectedShapes))
        if yes == QtWidgets.QMessageBox.warning( self, self.tr("Attention"), msg, yes | no, yes ):
            self.remLabels(self.canvas.deleteSelected())
            self.canvas_shape_moved()
            if self.noShapes():
                for action in self.struct_actions.onShapesPresent:
                    action.setEnabled(False)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.listwidget_label.clearSelection()
        for shape in self.canvas.selectedShapes:
            self.addLabel(shape)
        self.canvas_shape_moved()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.canvas_shape_moved()

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else "."

        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            defaultOpenDirPath = ( osp.dirname(self.filename) if self.filename else "." )

        # defaultOpenDirPath = r'D:\proj_pill\pill_shape'
        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % __appname__,
                defaultOpenDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        self.importDirImages(targetDirPath)

    @property
    def imageList(self):
        lst = []
        for i in range(self.listwidget_filelist.count()):
            item = self.listwidget_filelist.item(i)
            lst.append(item.text())
        return lst

    def importDroppedImageFiles(self, imageFiles):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        self.filename = None
        for file in imageFiles:
            if file in self.imageList or not file.lower().endswith(
                tuple(extensions)
            ):
                continue
            label_file = osp.splitext(file)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            item = QtWidgets.QListWidgetItem(file)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
                label_file
            ):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.listwidget_filelist.addItem(item)

        if len(self.imageList) > 1:
            self.struct_actions.openNextImg.setEnabled(True)
            self.struct_actions.openPrevImg.setEnabled(True)

        self.openNextImg()

    def importDirImages(self, dirpath, pattern=None, load=True):
        self.struct_actions.openNextImg.setEnabled(True)
        self.struct_actions.openPrevImg.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.filename = None
        self.listwidget_filelist.clear()
        for filename in self.scanAllImages(dirpath):
            if pattern and pattern not in filename:
                continue
            label_file = osp.splitext(filename)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            item = QtWidgets.QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if QtCore.QFile.exists(label_file) and LabelFile.is_label_file( label_file):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.listwidget_filelist.addItem(item)
        self.openNextImg(load=load)

    def scanAllImages(self, folderPath):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        images = []
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = osp.join(root, file)
                    images.append(relativePath)
        images.sort(key=lambda x: x.lower())
        return images

    def btnDigitClicked(self, id):
        for button in self.group_digits.buttons():
            if button is self.group_digits.button(id):
                self.digit_selected = button.text()
                print(button.text() + " Clicked!")