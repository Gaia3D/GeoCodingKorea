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
        self.dlg = GeoCodingKoreaDialog(iface, iface.mainWindow())

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GeoCoding for Korea')
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
                + u'속성 테이블은 엑셀 파일이나 CSV 파일을 레이어 트리에 끌어다 놓아 만드실 수 있습니다.')
            return

        self.dlg.fill_crs()
        self.dlg.fill_addr_column(layer)
        # 테이블에 컬럼과 테이터를 채워 넣기
        self.dlg.draw_data_table(layer)

        # show the dialog
        self.dlg.show()
        #self.dlg.progressBar.hide()

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

