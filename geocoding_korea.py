# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCodingKorea
                                 A QGIS plugin
 Convert Korean address to geomery
                              -------------------
        begin                : 2015-06-11
        git sha              : $Format:%H$
        copyright            : (C) 2015 by BJ Jang/Gaia3D
        email                : jangbi882@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
# import resources_rc
# Import the code for the dialog
from geocoding_korea_dialog import GeoCodingKoreaDialog
import os.path
import resources_rc

class GeoCodingKorea:
    """QGIS Plugin Implementation."""
    _crs_name = None
    _address_col_name =None
    _sim_ratio_column = "sim_ratio"
    _service_name_column = "svc_name"
    _request_addr_column = "req_addr"
    _response_addr_column = "res_addr"

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GeoCodingKorea_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = GeoCodingKoreaDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GeoCoding for Korea')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GeoCodingKorea')
        self.toolbar.setObjectName(u'GeoCodingKorea')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GeoCodingKorea', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GeoCodingKorea/icon.png'
        self.add_action(
            icon_path,
            text=self.tr('GeoCoding for Korea'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr('&GeoCoding for Korea'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def alert(self, msg):
         QMessageBox.warning(self.iface.mainWindow(), self.tr('GeoCoding for Korea'), msg)

    def run(self):
        # 만약 속성 테이블이 현재 테이블이 아니라면 경고 띠우고 종료
        layer = self.iface.activeLayer()
        if layer == None \
                or layer.type() != layer.VectorLayer \
                or layer.geometryType() != QGis.NoGeometry:
            self.alert(
                u'레이어 트리에서 속성 테이블을 선택후 실행해 주십시오.\n'
                +u'속성 테이블은 엑셀 파일이나 CSV파일을 레이어 트리에 끌어다 놓아 만드실 수 있습니다.')
            return

        # 최근 사용한 좌표계 정보 채워 넣기
        # http://gis.stackexchange.com/questions/86796/get-list-of-crs-in-qgis-by-python
        crs_list = QSettings().value('UI/recentProjectionsAuthId')
        self.dlg.cmbCrs.clear()
        self.dlg.cmbCrs.addItems(crs_list)

        # Project의 좌표계를 기본으로 설정
        crs_index = 0
        crr_crs = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()
        if not self._crs_name:
            self._crs_name = crr_crs

        for i in range(len(crs_list)):
            crs = crs_list[i]
            if crs == crr_crs:
                crs_index = i
        self.dlg.cmbCrs.setCurrentIndex(crs_index)

        # 원본 주소로 사용 가능한 텍스트 컬럼 확인
        provider = layer.dataProvider()
        if not provider:
            return

        address_col_index = 0
        fields = provider.fields()
        field_name_list = []
        for i in range(len(fields)):
            field = fields[i]
            field_type = field.type()
            # 문자열 타입만 리스트에 추가
            if field_type != QVariant.String:
                continue
            field_name = field.name()
            if not self._address_col_name:
                self._address_col_name = field_name
            if self._address_col_name == field_name:
                address_col_index = i
            field_name_list.append(field_name)

        # 원본 주소 컬럼 선택 가능하게 채우기
        self.dlg.cmbAddrCol.clear()
        self.dlg.cmbAddrCol.addItems(field_name_list)
        self.dlg.cmbAddrCol.setCurrentIndex(address_col_index)

        # 새로 만들 컬럼명 설정
        self.dlg.ledtSimRatio.setText(self._sim_ratio_column)
        self.dlg.ledtServiceName.setText(self._service_name_column)
        self.dlg.ledtCleanAddr.setText(self._request_addr_column)
        self.dlg.ledtRetAddr.setText(self._response_addr_column)

        # TODO: 테이블에 컬럼과 테이터를 채워 넣기
        self.drawDataTable(layer)

        # show the dialog
        self.dlg.show()
        self.dlg.progressBar.hide()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.

            # TODO: 모든 항목들이 선택되었는지 확인

            # TODO: 새로 만들 컬럼들 확인 해 없으면 만들기

            # TODO: 주소 컬럼에서 변환할 주소 수집

            # TODO: 반환된 정보를 각 컬럼에 반영

            pass


    def drawDataTable(self, layer): # Called when user switches tabWidget to the Table Preview
        provider = layer.dataProvider()
        fields = provider.fields()
        col_count = len(fields)
        row_count = provider.featureCount()
        self.dlg.dataTable.clear()
        self.dlg.repaint()
        self.dlg.dataTable.setColumnCount(col_count)
        self.dlg.dataTable.setRowCount(row_count)
        header = []
        for i in fields:
          header.append(i.name())
        self.dlg.dataTable.setHorizontalHeaderLabels(header)
        self.dlg.progressBar.setRange (0, row_count+1)
        self.dlg.progressBar.setFormat(self.tr('Drawing table') +': %p%')
        formatting = False
        if formatting: # slower procedure, with formatting the table items
          """
          for i in range(len(self.data)):
            self.progressBar.setValue(i+1)
            for j in range(len(self.data[i])):
              item = QTableWidgetItem(unicode(self.data[i][j] or 'NULL'))
              item.setFlags(Qt.ItemIsSelectable)
              if fields[i].type() == 6 or fields[i].type() == 2:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
              self.dataTable.setItem(j,i,item)
          """
        else: # about 25% faster procedure, without formatting
          i = 0
          for f in layer.getFeatures():
              self.dlg.progressBar.setValue(i+1)
              for j in range(col_count):
                  val = f[j]
                  self.dlg.dataTable.setItem(i,j,QTableWidgetItem(unicode(val or 'NULL')))
              i += 1
        self.dlg.dataTable.resizeColumnsToContents()
        self.needsRedraw = False
        self.dlg.progressBar.reset()
