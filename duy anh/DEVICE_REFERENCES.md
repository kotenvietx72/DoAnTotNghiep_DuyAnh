# Dòng điện thiết bị tham chiếu

Đối chiếu ngày **01/11/2026**. Đây là bộ model tham chiếu cho mô phỏng, không phải thông số đo từ thiết bị vật lý của người dùng. Các dòng đều tính ở **phía nguồn AC**; không cộng dòng đầu ra DC của adapter vào tổng phòng.

| Thiết bị áp dụng | Model tham chiếu | Dòng cài đặt (A) | Điện áp tài liệu (V) | Căn cứ / nguồn hãng |
|---|---|---:|---|---|
| 6 đèn phòng học | Philips CorePro UniFit T8 929004434038 | 0,095 | 220–240 | Dòng danh định 95 mA. [Signify](https://www.signify.com/global/prof/led-lamps-and-tubes/led-tubes/philips-corepro-led-tube-unifit-em-mains-t8/929004434038_EU/product) |
| Đèn kí túc xá, bảo vệ | Philips MASTER LEDtube 929001239402 | 0,043 | 220–240 | Dòng tối đa 43 mA, tối thiểu 36 mA. [Datasheet Philips](https://www.assets.lighting.philips.com/is/content/PhilipsLighting/fp929001239402-pss-global) |
| Đèn bàn | Philips Essential E27 929001893271 | 0,030 | 220–240 | Dòng danh định 30 mA. [Datasheet Philips](https://www.assets.signify.com/is/content/PhilipsLighting/fp929001893271-pss-global) |
| 4 quạt trần phòng học | Panasonic F-56XZ2 | 0,352 | 220 / 50 Hz | **Ước tính** từ mức đầu vào cao trong bảng hãng với PF giả định 0,8; hãng không nêu trực tiếp A ở trang này. [Thông số Panasonic](https://www.panasonic.com/mea/en/consumer/air-solutions/fans/ceiling-fan/standard-series.specs.html) |
| Quạt kí túc xá, bảo vệ | Panasonic F-409K | 0,234 | 220–240 / 50 Hz | **Quy đổi** theo thông số 220 V và hệ số 0,99 trong bảng hướng dẫn; giá trị làm tròn. [Hướng dẫn Panasonic](https://www.panasonic.com/content/dam/panasonic/vn/vi/pim/dam/F-/F-409K/F-409K-PP/ast-2100716.pdf) |
| 2 điều hòa phòng học | Panasonic CU/CS-PU18CKH-8D | 7,9 | 220 | Cường độ dòng điện định mức tại 220 V. [Panasonic chính hãng](https://store.apac.panasonic.com/vn/cu-cs-pu18ckh-8d.html) |
| Điều hòa kí túc xá | Panasonic CU/CS-PU12CKH-8D | 4,8 | 220 | Cường độ dòng điện định mức tại 220 V. [Panasonic chính hãng](https://store.apac.panasonic.com/vn/cu-cs-pu12ckh-8d.html) |
| Điều hòa bảo vệ | Panasonic CU/CS-PU9CKH-8D | 3,7 | 220 | Cường độ dòng điện trong thông số sản phẩm. [Panasonic chính hãng](https://store.apac.panasonic.com/vn/comboac11.html) |
| Máy chiếu | Epson PowerLite Home Cinema 3010+ | 1,7 | 200–240 | Dòng định mức trong mục Electrical, trang 73. [Epson](https://files.support.epson.com/pdf/plhc3010pl/plhc3010plug.pdf#page=73) |
| Máy tính giáo viên, máy tính trực | Dell OptiPlex 3050 SFF | 1,5 | 90–264 | Bảng đầu vào AC ghi 3 / 1,5 A; lấy mức nhánh điện áp cao. Đây là thông số nguồn, không phải mức tiêu thụ trung bình khi nhàn rỗi. [Dell](https://dl.dell.com/topicspdf/optiplex-3050-desktop_owners-manual3_en-us.pdf) |
| Máy tính kí túc xá | Dell Latitude 3540, adapter USB-C | 1,7 | 100–240 | **Giới hạn dòng AC đầu vào** của adapter; tải thực tế thay đổi theo sạc và tác vụ. [Dell](https://www.dell.com/support/manuals/en-ie/latitude-15-3540-laptop/latitude_3540_ss/power-adapter?guid=guid-8d0a8991-4a14-4370-9908-2d2292d6c2f6&lang=en-us) |
| Bình nóng lạnh | Ferroli QQ Evo 30 | 11,364 | 220 | **Quy đổi** thông số gia nhiệt của hãng, tải thuần trở PF≈1, khi thanh nhiệt đang hoạt động. [Ferroli](https://ferroli.com.vn/wp-content/uploads/2023/01/QQ161226.pdf) |
| Ấm siêu tốc | Philips HD9306/03 | 8,182 | 220 | **Quy đổi** thông số gia nhiệt của hãng với PF≈1 khi đang đun. [Philips](https://www.documents.philips.com/assets/20210917/f113805a9e7a4dada82fada601105137.pdf) |
| Màn hình camera | Dell P2422H | 1,5 | 100–240 | Dòng đầu vào AC trong hướng dẫn; không coi là số đo tức thời ở một độ sáng cụ thể. [Dell](https://dl.dell.com/manuals/all-products/esuprt_electronics_accessories/esuprt_electronics_accessories_monitor/esuprt_monitor_p_series/dell-p2722h-monitor_user%27s-guide_en-us.pdf) |
| Camera và adapter | MEAN WELL GST18A12-P1J | 0,3 | Đầu vào 85–264, điểm tham chiếu 230 | Lấy **AC CURRENT 0,3 A tại 230 VAC** của adapter; dùng làm tham chiếu gần đúng cho mạng 220 V, không phải dòng DC 1,5 A của camera. [MEAN WELL](https://www.meanwell.com/Upload/PDF/GST18A/GST18A-SPEC.PDF) |

## Cách áp dụng

- Mô hình cộng dòng tham chiếu của thiết bị đang bật. Công tắc Tắt được hiểu là ngắt khỏi nhánh, nên tính 0 A và không tính dòng chờ.
- Các trị số trong cột “Dòng cài đặt” là giá trị mới mặc định. Mức đã tự chỉnh trong dữ liệu cũ được giữ tương đương khi chuyển sang A.
- Không dùng dòng **inrush** làm dòng hoạt động liên tục. Adapter, máy tính, màn hình và điều hòa không có mức dòng cố định trong mọi điều kiện thực tế; mô hình ON/OFF giữ một giá trị tham chiếu để trình diễn.
- Giá trị có ghi **ước tính/quy đổi** không được trình bày là phép đo hay A do hãng công bố trực tiếp. Khi có nhãn thiết bị cụ thể hoặc số đo ampe kìm, có thể sửa lại trong Cài đặt.
- Model, liên kết nguồn và phương pháp được lưu trong `device_references.py`, đi cùng mỗi thiết bị ở trường `reference` của API.
