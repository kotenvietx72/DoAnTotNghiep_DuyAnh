"""Thông số tham chiếu nhà sản xuất; chi tiết và điều kiện đo tại DEVICE_REFERENCES.md."""


def reference(model, current_a, source_url, basis, voltage_range_v):
    return {"model": model, "current_a": current_a, "source_url": source_url,
            "basis": basis, "voltage_range_v": voltage_range_v}


REFERENCE_PROFILES = {
    "room_led": reference("Philips CorePro UniFit T8 929004434038", .095,
        "https://www.signify.com/global/prof/led-lamps-and-tubes/led-tubes/philips-corepro-led-tube-unifit-em-mains-t8/929004434038_EU/product", "rated_ac", [220,240]),
    "small_led": reference("Philips MASTER LEDtube 929001239402", .043,
        "https://www.assets.lighting.philips.com/is/content/PhilipsLighting/fp929001239402-pss-global", "maximum_ac", [220,240]),
    "desk_led": reference("Philips Essential E27 929001893271", .030,
        "https://www.assets.signify.com/is/content/PhilipsLighting/fp929001893271-pss-global", "rated_ac", [220,240]),
    "ceiling_fan": reference("Panasonic F-56XZ2", .352,
        "https://www.panasonic.com/mea/en/consumer/air-solutions/fans/ceiling-fan/standard-series.specs.html", "estimate_pf_0.8", [220,220]),
    "standing_fan": reference("Panasonic F-409K", .234,
        "https://www.panasonic.com/content/dam/panasonic/vn/vi/pim/dam/F-/F-409K/F-409K-PP/ast-2100716.pdf", "derived_pf_0.99", [220,240]),
    "ac_classroom": reference("Panasonic CU/CS-PU18CKH-8D", 7.9,
        "https://store.apac.panasonic.com/vn/cu-cs-pu18ckh-8d.html", "rated_ac", [220,220]),
    "ac_dormitory": reference("Panasonic CU/CS-PU12CKH-8D", 4.8,
        "https://store.apac.panasonic.com/vn/cu-cs-pu12ckh-8d.html", "rated_ac", [220,220]),
    "ac_security": reference("Panasonic CU/CS-PU9CKH-8D", 3.7,
        "https://store.apac.panasonic.com/vn/comboac11.html", "rated_ac", [220,220]),
    "projector": reference("Epson PowerLite Home Cinema 3010+", 1.7,
        "https://files.support.epson.com/pdf/plhc3010pl/plhc3010plug.pdf#page=73", "rated_ac", [200,240]),
    "computer": reference("Dell OptiPlex 3050 SFF", 1.5,
        "https://dl.dell.com/topicspdf/optiplex-3050-desktop_owners-manual3_en-us.pdf", "high_voltage_ac_input_rating", [90,264]),
    "laptop": reference("Dell Latitude 3540 USB-C adapter", 1.7,
        "https://www.dell.com/support/manuals/en-ie/latitude-15-3540-laptop/latitude_3540_ss/power-adapter?guid=guid-8d0a8991-4a14-4370-9908-2d2292d6c2f6&lang=en-us", "maximum_ac_input", [100,240]),
    "heater": reference("Ferroli QQ Evo 30", 11.364,
        "https://ferroli.com.vn/wp-content/uploads/2023/01/QQ161226.pdf", "derived_resistive", [220,220]),
    "kettle": reference("Philips HD9306/03", 8.182,
        "https://www.documents.philips.com/assets/20210917/f113805a9e7a4dada82fada601105137.pdf", "derived_resistive", [220,220]),
    "monitor": reference("Dell P2422H", 1.5,
        "https://dl.dell.com/manuals/all-products/esuprt_electronics_accessories/esuprt_electronics_accessories_monitor/esuprt_monitor_p_series/dell-p2722h-monitor_user%27s-guide_en-us.pdf", "ac_input_rating", [100,240]),
    "camera": reference("Camera + MEAN WELL GST18A12-P1J", .3,
        "https://www.meanwell.com/Upload/PDF/GST18A/GST18A-SPEC.PDF", "adapter_ac_at_230v", [85,264]),
}

DEVICE_REFERENCE_KEYS = {
    "r1": {**{f"light{i}": "room_led" for i in range(1,7)}, **{f"fan{i}": "ceiling_fan" for i in range(1,5)},
           "ac1":"ac_classroom", "ac2":"ac_classroom", "projector":"projector", "computer":"computer"},
    "r2": {"light1":"small_led", "light2":"small_led", "desk_light1":"desk_led", "desk_light2":"desk_led",
           "fan1":"standing_fan", "fan2":"standing_fan", "ac":"ac_dormitory", "heater":"heater",
           "laptop1":"laptop", "laptop2":"laptop", "kettle":"kettle"},
    "r3": {"light1":"small_led", "light2":"small_led", "fan":"standing_fan", "ac":"ac_security",
           "computer":"computer", "monitor":"monitor", "camera":"camera", "kettle":"kettle"},
}

# Chỉ dùng để nhận dạng mặc định của phiên bản trước khi chuyển dữ liệu cũ.
LEGACY_DEVICE_DEFAULTS = {
    "r1": {**{f"light{i}":40 for i in range(1,7)}, **{f"fan{i}":75 for i in range(1,5)},
           "ac1":1800, "ac2":1800, "projector":280, "computer":250},
    "r2": {"light1":24, "light2":24, "desk_light1":12, "desk_light2":12, "fan1":60, "fan2":60,
           "ac":1500, "heater":2500, "laptop1":65, "laptop2":65, "kettle":1500},
    "r3": {"light1":20, "light2":20, "fan":65, "ac":1000, "computer":250, "monitor":60, "camera":12, "kettle":1500},
}
