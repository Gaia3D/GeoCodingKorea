# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoCodingKoreaDialog
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

import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'geocoding_korea_dialog_base.ui'))


class GeoCodingKoreaDialog(QtGui.QDialog, FORM_CLASS):
    # Member variable
    _crs_name = None
    _address_col_name = None
    _sim_ratio_column = "sim_ratio"
    _service_name_column = "svc_name"
    _request_addr_column = "req_addr"
    _response_addr_column = "res_addr"

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(GeoCodingKoreaDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.iface = iface
        self.setupUi(self)
        self.ledtSimRatio.setText(self._sim_ratio_column)
        self.ledtServiceName.setText(self._service_name_column)
        self.ledtCleanAddr.setText(self._request_addr_column)
        self.ledtRetAddr.setText(self._response_addr_column)

    # 좌표계 정보 채우기
    def fill_crs(self):
        # 최근 사용한 좌표계 정보 채워 넣기. 좌표계 전체를 다 뿌리면 너무 많다!
        # http://gis.stackexchange.com/questions/86796/get-list-of-crs-in-qgis-by-python
        crs_list = QSettings().value('UI/recentProjectionsAuthId')
        self.cmbCrs.clear()
        self.cmbCrs.addItems(crs_list)

        # Project의 좌표계를 기본으로 설정
        crs_index = 0
        crr_crs = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()
        if not self._crs_name:
            self._crs_name = crr_crs

        for i in range(len(crs_list)):
            crs = crs_list[i]
            if crs == crr_crs:
                crs_index = i
        self.cmbCrs.setCurrentIndex(crs_index)

    # 원본 주소로 사용 가능한 텍스트 컬럼 확인
    def fill_addr_column(self, layer):
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
        self.cmbAddrCol.clear()
        self.cmbAddrCol.addItems(field_name_list)
        self.cmbAddrCol.setCurrentIndex(address_col_index)

    def draw_data_table(self, layer):
        provider = layer.dataProvider()
        fields = provider.fields()
        col_count = len(fields)
        row_count = provider.featureCount()
        self.dataTable.clear()
        self.repaint()
        self.dataTable.setColumnCount(col_count)
        self.dataTable.setRowCount(row_count)
        header = []
        for i in fields:
            header.append(i.name())
        self.dataTable.setHorizontalHeaderLabels(header)
        self.progressBar.setRange(0, row_count+1)
        self.progressBar.setFormat(self.tr('Drawing table') + ': %p%')

        if row_count <= 200:
            formatting = True
        else:
            formatting = False
        i = 0
        for f in layer.getFeatures():
            self.progressBar.setValue(i+1)
            for j in range(col_count):
                val = f[j]
                item = QTableWidgetItem(unicode(val or 'NULL'))
                item.setFlags(Qt.ItemIsSelectable)
                if formatting and (fields[j].type() == 6 or fields[j].type() == 2):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.dataTable.setItem(i, j, item)
            i += 1
        self.dataTable.resizeColumnsToContents()
        self.progressBar.reset()
