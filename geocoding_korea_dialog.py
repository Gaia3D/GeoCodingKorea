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
import urllib2
import json
from threading import Thread
from qgis.core import QgsApplication


def force_gui_update():
    QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'geocoding_korea_dialog_base.ui'))


class GeoCodingKoreaDialog(QtGui.QDialog, FORM_CLASS):
    # Member variable
    iface = None
    layer = None
    _crs_name = None
    _address_col_name = None
    _sim_ratio_column = "sim_ratio"
    _service_name_column = "svc_name"
    _request_addr_column = "req_addr"
    _response_addr_column = "ret_addr"
    _sd_column = 'sd'

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
        self.ledtSd.setText(self._sd_column)
        self.btnSave.setEnabled(False)
        self._connect_action()

    def _connect_action(self):
        self.connect(self.btnRun, SIGNAL("clicked()"), self._on_btn_run)
        self.connect(self.btnSave, SIGNAL("clicked()"), self._on_btn_save)

    def set_layer(self, layer):
        self.layer = layer
        self._fill_addr_column()
        self._fill_crs()
        self.ledtLayerName.setText(layer.name()+'_geocoding')
        self._draw_data_table()
        self.progressBar.reset()

    def show(self):
        if not self.layer:
            raise Exception("set_layer(layer) function must be call first.")
        super(GeoCodingKoreaDialog, self).show()

    def alert(self, msg):
         QMessageBox.warning(self.iface.mainWindow(), self.tr('GeoCoding for Korea'), msg)

    # 좌표계 정보 채우기
    def _fill_crs(self):
        # 최근 사용한 좌표계 정보 채워 넣기. 좌표계 전체를 다 뿌리면 너무 많다!
        # http://gis.stackexchange.com/questions/86796/get-list-of-crs-in-qgis-by-python
        crs_list = QSettings().value('UI/recentProjectionsAuthId')
        self.cmbCrs.clear()
        self.cmbCrs.addItems(crs_list)

        # Project의 좌표계를 기본으로 설정
        if not self._crs_name:
            self._crs_name = self.iface.mapCanvas().mapRenderer().destinationCrs().authid()
        crs_index = 0

        for i in range(len(crs_list)):
            crs = crs_list[i]
            if crs == self._crs_name:
                crs_index = i
        self.cmbCrs.setCurrentIndex(crs_index)

    # 원본 주소로 사용 가능한 텍스트 컬럼 확인
    def _fill_addr_column(self):
        if not self.layer:
            raise Exception("self.layer must be set first.")

        self.provider = self.layer.dataProvider()
        if not self.provider:
            raise Exception("Selected layer dose not have provider.")

        address_col_index = 0
        self.fields = self.provider.fields()
        self.field_name_list = []
        for i in range(len(self.fields)):
            field = self.fields[i]
            field_type = field.type()
            # 문자열 타입만 리스트에 추가
            if field_type != QVariant.String:
                continue
            field_name = field.name()
            if not self._address_col_name:
                self._address_col_name = field_name
            if self._address_col_name == field_name:
                address_col_index = i
            self.field_name_list.append(field_name)

        # 원본 주소 컬럼 선택 가능하게 채우기
        self.cmbAddrCol.clear()
        self.cmbAddrCol.addItems(self.field_name_list)
        self.cmbAddrCol.setCurrentIndex(address_col_index)

    def _draw_data_table(self):
        if not self.layer:
            raise Exception("self.layer must be set first.")

        self.provider = self.layer.dataProvider()
        fields = self.provider.fields()
        col_count = len(fields)
        self.row_count = self.provider.featureCount()
        self.dataTable.clear()
        self.repaint()
        self.dataTable.setColumnCount(col_count)
        self.dataTable.setRowCount(self.row_count)
        header = []
        for i in fields:
            header.append(i.name())
        self.dataTable.setHorizontalHeaderLabels(header)

        if self.row_count <= 200:
            formatting = True
        else:
            formatting = False
        i = 0
        for f in self.layer.getFeatures():
            for j in range(col_count):
                val = f[j]
                item = QTableWidgetItem(unicode(val or 'NULL'))
                item.setFlags(Qt.ItemIsSelectable)
                if formatting and (fields[j].type() == 6 or fields[j].type() == 2):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.dataTable.setItem(i, j, item)
            i += 1
        self.dataTable.resizeColumnsToContents()

    def _on_btn_run(self):
        # 선택정보 수집
        self._address_col_name = self.cmbAddrCol.currentText()
        self._crs_name = self.cmbCrs.currentText()
        self._sim_ratio_column = self.ledtSimRatio.text()
        self._service_name_column = self.ledtServiceName.text()
        self._request_addr_column = self.ledtCleanAddr.text()
        self._response_addr_column = self.ledtRetAddr.text()
        self._sd_column = self.ledtSd.text()

        msg = u"'{}' 컬럼을 원본 주소 컬럼으로 이용해 지오코딩을 하시겠습니까?".format(self._address_col_name)
        reply = QtGui.QMessageBox.question(self, 'Message', msg,
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return

        self.progressBar.setRange(0, self.row_count)
        self.progressBar.setFormat(self.tr('GeoCoding') + ': %p%')
        self.progressBar.setValue(1)
        force_gui_update()

        # 새로 만들 컬럼들 확인해 없으면 만들기
        if self._request_addr_column not in self.field_name_list:
            self.field_name_list.append(self._request_addr_column)
            self.dataTable.setColumnCount(len(self.field_name_list))
            item = QTableWidgetItem(self._request_addr_column)
            i = len(self.field_name_list)-1
            self.i_request_addr_column = i
            self.dataTable.setHorizontalHeaderItem(i, item)
        else:
            self.i_request_addr_column = self.field_name_list.index(self._request_addr_column)

        if self._response_addr_column not in self.field_name_list:
            self.field_name_list.append(self._response_addr_column)
            self.dataTable.setColumnCount(len(self.field_name_list))
            item = QTableWidgetItem(self._response_addr_column)
            i = len(self.field_name_list)-1
            self.i_response_addr_column = i
            self.dataTable.setHorizontalHeaderItem(i, item)
        else:
            self.i_response_addr_column = self.field_name_list.index(self._response_addr_column)

        if self._sim_ratio_column not in self.field_name_list:
            self.field_name_list.append(self._sim_ratio_column)
            self.dataTable.setColumnCount(len(self.field_name_list))
            item = QTableWidgetItem(self._sim_ratio_column)
            i = len(self.field_name_list)-1
            self.i_sim_ratio_column = i
            self.dataTable.setHorizontalHeaderItem(i, item)
        else:
            self.i_sim_ratio_column = self.field_name_list.index(self._sim_ratio_column)

        if self._service_name_column not in self.field_name_list:
            self.field_name_list.append(self._service_name_column)
            self.dataTable.setColumnCount(len(self.field_name_list))
            item = QTableWidgetItem(self._service_name_column)
            i = len(self.field_name_list)-1
            self.i_service_name_column = i
            self.dataTable.setHorizontalHeaderItem(i, item)
        else:
            self.i_service_name_column = self.field_name_list.index(self._service_name_column)

        if self._sd_column not in self.field_name_list:
            self.field_name_list.append(self._sd_column)
            self.dataTable.setColumnCount(len(self.field_name_list))
            item = QTableWidgetItem(self._sd_column)
            i = len(self.field_name_list)-1
            self.i_sd_column = i
            self.dataTable.setHorizontalHeaderItem(i, item)
        else:
            self.i_sd_column = self.field_name_list.index(self._sd_column)

        # 주소 컬럼에서 변환할 주소 찾아 변환 요청
        # 멀티쓰레드로 한꺼번에 요청
        i = 0
        self.num_processed = 0
        self.data_list = self.row_count * [None]
        for f in self.layer.getFeatures():
            org_addr = f[self._address_col_name]
            # self.call_geocoding(i, org_addr)
            th = Thread(target=self.call_geocoding, args=(i, org_addr, ))
            th.start()
            i += 1

        # 쓰레드가 주는 결과를 찾아 다 올때까지 테이블 업데이트
        self.update_table()

        self.progressBar.reset()
        self.alert( u"변환이 완료되었습니다.\n"
                    u"주소 유사도가 낮은 주소는 편집해 개선 가능합니다.\n"
                    u"현재 결과에 만족하시면 [레이어로 만들기]을 눌러 작업을 완료하세요.\n"
                    u"만들어진 레이어는 메모리 레이어이므로 파일이나 DB에 저장하셔야 합니다.")
        self.btnSave.setEnabled(True)
        self.lblMessage.setText(u"주소 유사도가 낮은 행은 원본 주소 컬럼의 주소를 수동으로 편집해서 개선 가능합니다.")

    def call_geocoding(self, i, address):
        encoded_str = urllib2.quote(address.encode("utf-8"))
        url = "http://geeps.krihs.re.kr/geocoding/api?q={}&id={}&crs=epsg:4326&format=json".format(encoded_str, i)
        response = urllib2.urlopen(url)
        header = response.info()
        data = response.read()
        dic = json.loads(data, "utf-8")
        dic["new"] = True
        dic["id"] = i
        self.data_list[i] = dic
        self.num_processed += 1

    def update_table(self):
        done_count = 0
        while done_count < self.row_count:
            done_count = 0
            dic = None
            for dic in self.data_list:
                if dic:
                    if dic["new"]:
                        break
                    else:
                        done_count += 1

            if not dic:
                continue

            dic["new"] = False
            i = dic["id"]
            req_addr = dic["q"]
            ret_addr = dic["address"]
            lng = dic["lng"]
            lat = dic["lat"]
            sim_ratio = dic["sim_ratio"]
            sd = dic["sd"]
            service = dic["geojson"]["properties"]["service"]

            item = QTableWidgetItem(unicode(req_addr or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignLeft)
            self.dataTable.setItem(i, self.i_request_addr_column, item)

            item = QTableWidgetItem(unicode(ret_addr or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignLeft)
            self.dataTable.setItem(i, self.i_response_addr_column, item)

            item = QTableWidgetItem(unicode(sim_ratio or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignRight)
            # 유사도에 따라 색 변경
            if sim_ratio < 90:
                bg_color = QColor(255, 0, 0)  # Red
            elif sim_ratio < 100:
                bg_color = QColor(255, 255, 0)  # Yellow
            else:
                bg_color = QColor(255, 255, 255)
            item.setBackground(QBrush(bg_color))
            self.dataTable.setItem(i, self.i_sim_ratio_column, item)

            item = QTableWidgetItem(unicode(service or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignHCenter)
            self.dataTable.setItem(i, self.i_service_name_column, item)

            item = QTableWidgetItem(unicode(sd or '0'))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignRight)
            if sd > 50:
                bg_color = QColor(255, 0, 0)  # Red
            else:
                bg_color = QColor(255, 255, 255)
            item.setBackground(QBrush(bg_color))
            self.dataTable.setItem(i, self.i_sd_column, item)

            self.progressBar.setValue(self.num_processed)
            force_gui_update()


    def _on_btn_save(self):
        # TODO: 저장루틴 구현
        pass