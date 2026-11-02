"""Chọn tải khả thi từ thiết bị; không thay công tắc thủ công hoặc ghi SQLite."""
from bisect import bisect_left
from decimal import Decimal
import random


class SimulationService:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self._cache = {}

    def select(self, room_id, devices, cfg, target, status, previous=()):
        # Giới hạn bộ nhớ theo phòng: cấu hình mới thay danh sách tổ hợp cũ.
        signature = (tuple((item["id"], item["current_a"]) for item in devices),
                     cfg["thresh_warn"], cfg["thresh_danger"])
        if room_id not in self._cache or self._cache[room_id][0] != signature:
            entries = [(Decimal(0), 0)]
            for index, item in enumerate(devices):
                current = Decimal(str(item["current_a"]))
                if current > 0:
                    entries += [(total + current, mask | (1 << index)) for total, mask in entries]
            groups = {key: {} for key in ("Safe", "Warning", "Danger", "all")}
            warn, danger = Decimal(str(cfg["thresh_warn"])), Decimal(str(cfg["thresh_danger"]))
            for total, mask in entries:
                total = round(total, 6)
                kind = "Danger" if total >= danger else "Warning" if total >= warn else "Safe"
                for key in (kind, "all"):
                    groups[key].setdefault(total, []).append(mask)
            self._cache[room_id] = (signature, {key: (sorted(values), values) for key, values in groups.items()})
        groups = self._cache[room_id][1]
        totals, masks = groups[status] if groups[status][0] else groups["all"]
        target = Decimal(str(target))
        position = bisect_left(totals, target)
        candidates = totals[max(0, position - 1):position + 1]
        distance = min(abs(total - target) for total in candidates)
        previous = set(previous)
        previous_mask = sum(1 << i for i, item in enumerate(devices) if item["id"] in previous)
        choices = [mask for total in candidates if abs(total - target) == distance for mask in masks[total]]
        changes = min((mask ^ previous_mask).bit_count() for mask in choices)
        mask = self.rng.choice([mask for mask in choices if (mask ^ previous_mask).bit_count() == changes])
        return {item["id"]: bool(mask & (1 << index)) for index, item in enumerate(devices)}
