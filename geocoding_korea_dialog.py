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
from qgis.core import *
import re

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
    _sim_ratio_column = u"주소유사도"
    _service_name_column = u"성공서비스"
    _request_addr_column = u"정제주소"
    _response_addr_column = u"반환주소"
    _sd_column = u'거리편차'
    i_address_column = None
    flag_edit_mode = False

    skyColor = QColor(242,255,255)
    red = QColor(255,0,0)
    yellow = QColor(255,255,0)
    white = QColor(255,255,255)
    liteYellow = QColor(255,255,215)

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
        self.connect(self.dataTable, SIGNAL("cellChanged(int, int)"), self._on_address_changed)
        self.connect(self.dataTable, SIGNAL("cellClicked(int, int)"), self._on_cell_clicked)
        self.connect(self.dataTable, SIGNAL("cellDoubleClicked(int, int)"), self._on_cell_double_clicked)

    def set_layer(self, layer):
        self.flag_edit_mode = False
        self.layer = layer
        self._fill_addr_column()
        self._fill_crs()
        self.ledtLayerName.setText(layer.name()+'_geocoding')
        self._draw_data_table()

    def show(self):
        if not self.layer:
            raise Exception("set_layer(layer) function must be call first.")
        self.progressBar.reset()
        self.lblMessage.setText(u"원본 주소 컬럼에 주소가 있는 컬럼을 선택하시고, [변환 시작!] 버튼을 눌러 주세요.")
        super(GeoCodingKoreaDialog, self).show()

    def close(self):
        # 내부 변수 제거
        self.data_list = None
        self.dataTable.setColumnCount(0)
        self.dataTable.setRowCount(0)
        self.btnSave.setEnabled(False)
        super(GeoCodingKoreaDialog, self).close()

    def alert(self, msg):
        QMessageBox.information(self.iface.mainWindow(), self.tr('GeoCoding for Korea'), msg)

    # 좌표계 정보 채우기
    def _fill_crs(self):
        # 최근 사용한 좌표계 정보 채워 넣기. 좌표계 전체를 다 뿌리면 너무 많다!
        # http://gis.stackexchange.com/questions/86796/get-list-of-crs-in-qgis-by-python
        crs_list = QSettings().value('UI/recentProjectionsAuthId')
        if not crs_list:
            crs_list = [u'EPSG:4326']
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
        self.flag_edit_mode = False
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
        self.flag_edit_mode = False

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

        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        self.progressBar.setRange(0, self.row_count)
        self.progressBar.setFormat(self.tr('GeoCoding') + ': %p%')
        self.progressBar.setValue(1)
        self.lblMessage.setText(u"지오코딩(주소->좌표변환)을 요청중입니다...")
        force_gui_update()

        # 원본 주소 컬럼 인덱스 확인
        self.i_address_column = self.field_name_list.index(self._address_col_name)

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
        self.num_processed = 0
        self.data_list = self.row_count * [None]
        for i in range(self.row_count):
            item = self.dataTable.item(i, self.i_address_column)
            org_addr = item.text()
            item.setBackground(QBrush(self.skyColor))
            item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled)
            # self.call_geocoding(i, org_addr)
            th = Thread(target=self.call_geocoding, args=(i, org_addr, ))
            th.start()

        # 쓰레드가 주는 결과를 찾아 다 올때까지 테이블 업데이트
        self.update_table()

        self.progressBar.reset()
        self.dataTable.resizeColumnsToContents()

        # 주소 편집시 이벤트 처리되게 설정
        self.flag_edit_mode = True
        QgsApplication.restoreOverrideCursor()

        self.alert( u"변환이 완료되었습니다.\n\n"
                    u"주소 유사도가 낮은 주소는 편집해 개선 가능합니다.\n"
                    u"현재 결과에 만족하시면 [레이어로 만들기]을 눌러 작업을 완료하세요.")
        self.btnSave.setEnabled(True)
        self.lblMessage.setText(u"주소 유사도가 낮은 행은 원본 주소 컬럼의 주소를 수동으로 편집해서 개선 가능합니다.")

    def call_geocoding(self, i, address):
        test_addr = re.sub(u"\s+", u"", address)
        if address == "" or address == "NULL" or test_addr == u"주소":
            dic = dict()
            dic["new"] = True
            dic["id"] = i
            self.data_list[i] = dic
            self.num_processed += 1
            return

        encoded_str = urllib2.quote(address.encode("utf-8"))
        url = "http://geeps.krihs.re.kr/geocoding/api?q={}&id={}&crs=epsg:4326&format=json".format(encoded_str, i)
        #url = "http://localhost/geocoding/api?q={}&id={}&crs=epsg:4326&format=json".format(encoded_str, i)

        try:
            response = urllib2.urlopen(url)
            header = response.info()
            data = response.read()
            dic = json.loads(data, "utf-8")
            dic["new"] = True
            dic["id"] = i
            self.data_list[i] = dic
            self.num_processed += 1

        except Exception:
            dic = dict()
            dic["new"] = True
            dic["id"] = i
            self.data_list[i] = dic
            self.num_processed += 1

    def update_table(self):
        self.flag_edit_mode = False
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

            self.update_row(dic)

    def update_row(self, dic):
        dic["new"] = False
        i = dic["id"]
        try:
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
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignLeft)
            item.setBackground(QBrush(self.liteYellow))
            self.dataTable.setItem(i, self.i_response_addr_column, item)

            item = QTableWidgetItem(unicode(sim_ratio or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignRight)
            # 유사도에 따라 색 변경
            if sim_ratio < 90:
                bg_color = self.red  # Red
            elif sim_ratio < 100:
                bg_color = self.yellow  # Yellow
            else:
                bg_color = self.white
            item.setBackground(QBrush(bg_color))
            self.dataTable.setItem(i, self.i_sim_ratio_column, item)
            # 원본 주소도 같은 색으로
            if sim_ratio < 100:
                self.dataTable.item(i, self.i_address_column).setBackground(QBrush(bg_color))
            else:
                self.dataTable.item(i, self.i_address_column).setBackground(QBrush(self.skyColor))

            item = QTableWidgetItem(unicode(service or ''))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignHCenter)
            self.dataTable.setItem(i, self.i_service_name_column, item)

            item = QTableWidgetItem(unicode(sd or '0'))
            item.setFlags(Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignRight)
            if sd > 50:
                bg_color = self.red  # Red
            else:
                bg_color = self.white
            item.setBackground(QBrush(bg_color))
            self.dataTable.setItem(i, self.i_sd_column, item)
        except Exception:
            item = QTableWidgetItem(unicode('Error'))
            item.setBackground(QBrush(self.yellow))
            self.dataTable.setItem(i, self.i_response_addr_column, item)

        self.progressBar.setValue(self.num_processed)
        force_gui_update()

    def _on_address_changed(self, i, j):
        if not self.flag_edit_mode:
            return
        if j != self.i_address_column:
            return

        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        org_addr = self.dataTable.item(i, j).text()
        self.call_geocoding(i, org_addr)

        dic = self.data_list[i]
        self.update_row(dic)

        QgsApplication.restoreOverrideCursor()
        self.lblMessage.setText(u"{}행 '{}' 재변환 완료. 주소 유사도 {}%".format(i+1, org_addr, dic["sim_ratio"]))

    def _on_cell_clicked(self, i, j):
        self.dataTable.clearSelection()
        self.dataTable.setRangeSelected(QTableWidgetSelectionRange(i, 0, i, len(self.field_name_list)-1), True)

    def _on_cell_double_clicked(self, i, j):
        if j == self.i_response_addr_column:
            msg = u"변환 주소를 원본 주소 컬럼에 복사하고 재변환 하시겠습니까?".format(self._address_col_name)
            reply = QtGui.QMessageBox.question(self, 'Message', msg,
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return

            new_addr = self.dataTable.item(i, self.i_response_addr_column).text()
            self.dataTable.item(i, self.i_address_column).setText(new_addr)

    def _on_btn_save(self):
        self.flag_edit_mode = False
        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        # 새 메모리 레이어 생성
        tCrs = self.cmbCrs.currentText()
        tLayerOption = "{0}?crs={1}&index=yes".format("Point", tCrs)
        tLayer = QgsVectorLayer(tLayerOption, self.ledtLayerName.text(), "memory")
        tProvider = tLayer.dataProvider()
        tLayer.startEditing()

        org_num_filed = len(self.provider.fields())
        attr_list = []
        for org_field in self.provider.fields():
            attr_list.append(QgsField(org_field.name(), org_field.type()))

        # 추가 컬럼 생성
        if self.i_request_addr_column >= org_num_filed:
            attr_list.append(QgsField(self._request_addr_column, QVariant.String))
            i_request_addr_column = len(attr_list)-1
        else:
            i_request_addr_column = self.i_response_addr_column

        if self.i_response_addr_column >= org_num_filed:
            attr_list.append(QgsField(self._response_addr_column, QVariant.String))
            i_response_addr_column = len(attr_list)-1
        else:
            i_response_addr_column = self.i_response_addr_column

        if self.i_sim_ratio_column >= org_num_filed:
            attr_list.append(QgsField(self._sim_ratio_column, QVariant.Int))
            i_sim_ratio_column = len(attr_list)-1
        else:
            i_sim_ratio_column = self.i_sd_column

        if self.i_service_name_column >= org_num_filed:
            attr_list.append(QgsField(self._service_name_column, QVariant.Int))
            i_service_name_column = len(attr_list)-1
        else:
            i_service_name_column = self.i_sd_column

        if self.i_sd_column >= org_num_filed:
            attr_list.append(QgsField(self._sd_column, QVariant.Int))
            i_sd_column = len(attr_list)-1
        else:
            i_sd_column = self.i_sd_column

        tProvider.addAttributes(attr_list)

        # 좌표계 변환 준비
        crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
        crsDest = QgsCoordinateReferenceSystem()
        i_tCrs = QSettings().value('UI/recentProjectionsAuthId').index(tCrs)
        tProj =  QSettings().value('UI/recentProjectionsProj4')[i_tCrs]
        crsDest.createFromProj4(tProj)
        xform = QgsCoordinateTransform(crsSrc, crsDest)

        t_feature_list = []
        i = 0
        for f in self.layer.getFeatures():
            dic = self.data_list[i]

            try:
                # 지오메트리 생성
                oPnt = QgsPoint(dic["lng"],dic["lat"])

                # 좌표계 변환
                tPnt = xform.transform(oPnt)

                iGeom = QgsGeometry.fromPoint(tPnt)

                tFeature = QgsFeature(tProvider.fields())
                tFeature.setGeometry(iGeom)

                # 데이터 부어 넣기
                for j_col in range(org_num_filed):
                    tFeature.setAttribute(j_col, f[j_col])

                # 원본 주소 컬럼 갱신
                tFeature.setAttribute(self.i_address_column, self.dataTable.item(i, self.i_address_column).text())

                # 추가된 컬럼에 값 넣기
                tFeature.setAttribute(i_request_addr_column, self.dataTable.item(i, self.i_request_addr_column).text())
                tFeature.setAttribute(i_response_addr_column, self.dataTable.item(i, self.i_response_addr_column).text())
                tFeature.setAttribute(i_sim_ratio_column, self.dataTable.item(i, self.i_sim_ratio_column).text())
                tFeature.setAttribute(i_service_name_column, self.dataTable.item(i, self.i_service_name_column).text())
                tFeature.setAttribute(i_sd_column, self.dataTable.item(i, self.i_sd_column).text())

                t_feature_list.append(tFeature)
            except Exception:
                pass  # 지오메트리 없는 경우

            i += 1

        tProvider.addFeatures(t_feature_list)

        tLayer.commitChanges()
        tLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(tLayer)
        self.iface.mapCanvas().setExtent(tLayer.extent())
        self.iface.mapCanvas().refresh()
        QgsApplication.restoreOverrideCursor()

        # 대화상자 닫기
        self.close()
        self.alert(u"레이어 생성 완료\n\n"
                   u"만들어진 레이어는 메모리 레이어이므로, \n"
                   u"보존을 위해서는 파일이나 DB에 저장하셔야 합니다.")
