GeoCoding for Korea
========================
This QGIS Plugin is just for Korean, that can convert address in table to geometry, but can only Koran address.

이 QGIS 용 플러그인은 문자열로 된 주소를 지오메트리(geometry)로 변경할 수 있습니다.

사용하시려면, 먼저 엑셀이나 CSV 파일을 QGIS의 레이어 트리로 끌어 놓아 속성 태이블을 만드시고,
웹 메뉴의 GeoCoding for Korea 메뉴나 툴바의 아이콘을 눌러 시작하시면 됩니다.

이 플러그인은 연구교육 공간정보기술 통합플랫폼 연구사업의 일부로 개발되었습니다.
주소 변환을 위해서 VWorld, Daum, Naver, Google의 GeoCoding API를 종합적으로 사용합니다. 
각 API를 서비스해주시는 기관들에 감사드립니다.

이 플러그인은 여러 GeoCoding API를 종합적으로 이용하기에 변환 성공률이 높고,
정제된 변환전 주소와 변환후 주소의 유사도를 비교하여 가장 유사한 주소를 반환한 서비스의 값을 택합니다.
또한, 정확치는 않지만 여러 서비스가 변환에 성공한 경우, 거리의 편차를 통계적으로 제시하여 정확도를 추측할 수 있게 합니다.


ICON
=======
Artist: PixelKit (http://www.iconarchive.com/show/gentle-edges-icons-by-pixelkit.html)
License: CC Attribution 4.0 (http://creativecommons.org/licenses/by/4.0/)
Icon Site: http://pixelkit.com