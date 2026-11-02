/* Sơ đồ 2D tự vẽ bằng SVG: nhìn từ trên xuống, không ảnh ngoài hay phối cảnh. */
(() => {
  const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const iconPaths = {
    light: '<path d="M8 15c-1-2-3-3-3-6a7 7 0 0 1 14 0c0 3-2 4-3 6l-1 3H9l-1-3Zm1 6h6M9 18h6M12 4v3"/>',
    fan: '<circle cx="12" cy="12" r="2"/><path d="M11 10C3 7 7 1 11 3c2 1 2 4 1 7m2 2c7-5 10 1 6 4-2 1-5 0-7-3m-2 1c1 9-6 8-6 3 0-2 2-4 5-4"/>',
    ac: '<rect x="2" y="4" width="20" height="11" rx="3"/><path d="M5 11h14M5 7h.01M7 18v3m5-3v3m5-3v3"/>',
    computer: '<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M8 21h8m-4-5v5M6 13h12"/>',
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8m-4-4v4M4 10h16M12 5v10"/>',
    projector: '<rect x="2" y="7" width="20" height="12" rx="3"/><circle cx="16" cy="13" r="3"/><path d="M5 11h3m-3 4h3M7 7V4h10v3"/>',
    heater: '<rect x="5" y="2" width="14" height="17" rx="5"/><path d="M9 19v3m6-3v3M9 7h6M12 10v4"/>',
    kettle: '<path d="M6 8h10l2 12H4L6 8Zm10 2h3a3 3 0 0 1 0 6h-2M9 5V3m4 2V3M7 8V6h8v2"/>',
    camera: '<rect x="2" y="5" width="14" height="10" rx="2"/><path d="m16 8 6-3v10l-6-3M9 15v5m-4 0h8"/>',
    desk_light: '<path d="m6 4 7-2 6 6-7 5-6-9ZM12 13l-5 6m0-9-3 9m-1 2h12M7 19h6"/>',
    laptop: '<rect x="4" y="3" width="16" height="13" rx="2"/><path d="m4 16-2 5h20l-2-5M2 21h20"/>',
  };

  // Tọa độ bố trí chỉ phục vụ bản vẽ; không thay đổi thiết bị/cấu hình đã lưu.
  const positions = {
    classroom: {light1:[330,273.6],light2:[590,273.6],light3:[890,273.6],
      light4:[330,486.4],light5:[590,486.4],light6:[890,486.4],
      fan1:[350,380],fan2:[610,380],fan3:[350,592.8],fan4:[610,592.8],
      ac1:[130,91.2],ac2:[870,91.2],projector:[500,159.6],computer:[190,174.8]},
    dormitory: {light1:[300,212.8],light2:[700,212.8],desk_light1:[210,615.6],desk_light2:[790,615.6],
      fan1:[300,532],fan2:[700,532],ac:[500,76],heater:[880,91.2],
      laptop1:[390,615.6],laptop2:[610,615.6],kettle:[880,372.4]},
    security: {light1:[350,205.2],light2:[660,205.2],fan:[220,494],ac:[180,114],
      computer:[320,304],monitor:[630,304],camera:[870,121.6],kettle:[800,509.2]},
  };
  const deviceLabels = {
    classroom:{light1:'Đ1',light2:'Đ2',light3:'Đ3',light4:'Đ4',light5:'Đ5',light6:'Đ6',fan1:'Q1',fan2:'Q2',fan3:'Q3',fan4:'Q4',ac1:'ĐH1',ac2:'ĐH2',projector:'MC',computer:'MT'},
    dormitory:{light1:'Đ1',light2:'Đ2',desk_light1:'ĐB1',desk_light2:'ĐB2',fan1:'Q1',fan2:'Q2',ac:'ĐH',heater:'NL',laptop1:'MT1',laptop2:'MT2',kettle:'ẤM'},
    security:{light1:'Đ1',light2:'Đ2',fan:'Q',ac:'ĐH',computer:'MT',monitor:'MH',camera:'CAM',kettle:'ẤM'},
  };
  const zones = {
    classroom:[['BẢNG',50,7],['KHU GIẢNG DẠY',50,28],['LỐI ĐI SAU LỚP',43,91],['CỬA',90,97]],
    dormitory:[['KHU NGỦ',30,53],['KHU NGỦ',70,53],['KHU TẮM',88,27],['KHU NƯỚC',88,57],['LỐI ĐI',50,88],['CỬA',50,97]],
    security:[['CỬA SỔ QUAN SÁT',50,7],['BÀN TRỰC',47,45],['KỆ NƯỚC',80,77],['LỐI ĐI',35,88],['CỬA',90,97]],
  };

  function deviceCode(kind, id) {
    return deviceLabels[kind]?.[id] || id;
  }

  function deviceIcon(kind, deviceId='') {
    const resolvedKind = kind === 'light' && deviceId.startsWith('desk_light') ? 'desk_light' : kind === 'computer' && deviceId.startsWith('laptop') ? 'laptop' : kind;
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${iconPaths[resolvedKind] || iconPaths.computer}</svg>`;
  }
  function modelLabel(name) {
    // Nhãn dài đã chuyển sang danh sách/aria-label; mã ngắn không chia dòng trên sơ đồ.
    return escape(name);
  }
  function desk(x,y,width=140) {
    return `<g transform="translate(${x} ${y})"><rect class="model-furniture" data-study-desk width="${width}" height="49" rx="6"/><rect class="model-chair" x="17" y="57" width="31" height="22" rx="5"/><rect class="model-chair" x="${width-48}" y="57" width="31" height="22" rx="5"/></g>`;
  }
  function bed(x,y) {
    return `<g transform="translate(${x} ${y})"><rect class="model-furniture" data-bed width="180" height="220" rx="7"/><rect class="model-bedding" x="8" y="8" width="164" height="204" rx="5"/><rect class="model-chair" x="17" y="16" width="146" height="44" rx="7"/><rect class="model-blanket" x="8" y="83" width="164" height="129" rx="4"/></g>`;
  }
  function furniture(kind) {
    if (kind === 'classroom') {
      let desks = '';
      for (const y of [315,425,535]) for (const x of [150,410,670]) desks += desk(x,y);
      return `<rect class="model-route" x="28" y="650" width="944" height="62"/><rect class="model-board" x="350" y="35" width="300" height="31" rx="3"/><rect class="model-furniture" x="107" y="139" width="165" height="62" rx="7"/>${desks}`;
    }
    if (kind === 'dormitory') {
      return `<rect class="model-route" data-circulation x="440" y="210" width="120" height="502"/>${bed(210,270)}${bed(610,270)}${desk(150,600,260)}${desk(590,600,260)}<path class="model-door" d="M800 24V145M800 225H976M800 145H880M800 225A80 80 0 0 1 880 145"/><rect class="model-furniture" x="825" y="340" width="110" height="66" rx="6"/><rect class="model-furniture" x="400" y="125" width="200" height="58" rx="5"/>`;
    }
    return `<rect class="model-route" x="32" y="610" width="808" height="100"/><rect class="model-furniture" x="190" y="275" width="545" height="81" rx="7"/><rect class="model-chair" x="295" y="380" width="31" height="22" rx="5"/><rect class="model-chair" x="600" y="380" width="31" height="22" rx="5"/><rect class="model-furniture" x="722" y="468" width="158" height="90" rx="6"/><rect class="model-furniture" x="825" y="290" width="105" height="150" rx="5"/>`;
  }
  function render(room, interactive=false) {
    const gridId = `floor-${room.id}-${interactive?'detail':'preview'}`;
    const controls = room.devices.map(item => {
      const [x,y] = positions[room.kind]?.[item.id] || [item.x,item.y];
      const tag = interactive ? 'button' : 'span';
      const label = `${item.name}: ${item.is_on?'đang bật':'đang tắt'}, ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A`;
      return `<${tag} class="model-device ${interactive?'model-control ':''}${item.is_on?'device-on':''}" data-model-device="${escape(item.id)}" ${interactive?`type="button" aria-pressed="${item.is_on}"`:''} aria-label="${escape(label)}" title="${escape(label)}" style="left:${x/10}%;top:${y/7.6}%"><span class="device-symbol">${deviceIcon(item.kind,item.id)}</span><span class="model-device-label">${modelLabel(deviceCode(room.kind,item.id))}</span></${tag}>`;
    }).join('');
    const wall = room.kind === 'dormitory' ? 'M24 716H440 M560 716H976V24H24V716' : 'M24 716H846 M956 716H976V24H24V716';
    const door = room.kind === 'dormitory' ? 'M560 716V596M440 716A120 120 0 0 1 560 596' : 'M956 716V606M846 716A110 110 0 0 1 956 606';
    const annotations = (zones[room.kind] || []).map(([name,x,y]) => `<span class="model-zone${name==='BẢNG'?' model-board-label':''}" data-model-zone="${escape(name)}" style="left:${x}%;top:${y}%">${escape(name)}</span>`).join('');
    return `<div id="${gridId}" class="room-scene" data-room-kind="${escape(room.kind)}" role="${interactive?'group':'img'}" aria-label="Sơ đồ ${escape(room.name)}"><svg class="model-plan" viewBox="0 0 1000 760" preserveAspectRatio="none" aria-hidden="true"><g class="model-furnishings">${furniture(room.kind)}</g><path class="model-wall" d="${wall}"/><path class="model-door" data-main-door d="${door}"/><path class="model-window" d="M24 250V440"/><path class="model-window-line" d="M24 250V440"/>${room.kind==='security'?'<path class="model-window" d="M340 24H660"/><path class="model-window-line" d="M340 24H660"/>':''}</svg>${annotations}${controls}</div>`;
  }
  function update(container, room, disabled=false, pendingDevices=new Set()) {
    for (const item of room.devices) {
      const node = container.querySelector(`[data-model-device="${item.id}"]`);
      if (!node) continue;
      node.classList.toggle('device-on',item.is_on);
      const label = `${item.name}: ${item.is_on?'đang bật':'đang tắt'}, ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A`;
      node.setAttribute('aria-label',label);
      node.setAttribute('title',label);
      if (node.tagName === 'BUTTON') {
        node.setAttribute('aria-pressed',String(item.is_on));
        node.disabled = disabled || pendingDevices.has(item.id);
        node.setAttribute('aria-disabled',String(node.disabled));
      }
    }
  }
  window.RoomModel = {render,update,deviceIcon,deviceCode,escape};
})();
