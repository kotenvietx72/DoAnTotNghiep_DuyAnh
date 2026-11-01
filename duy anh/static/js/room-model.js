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
  };

  // Tọa độ bố trí chỉ phục vụ bản vẽ; không thay đổi thiết bị/cấu hình đã lưu.
  const positions = {
    classroom: {light1:[255,170],light2:[435,170],light3:[615,170],
      light4:[255,280],light5:[435,280],light6:[615,280],
      fan1:[340,250],fan2:[520,250],fan3:[340,385],fan4:[520,385],
      ac1:[160,102],ac2:[660,102],projector:[420,110],computer:[155,448]},
    dormitory: {light1:[310,175],light2:[515,175],desk_light1:[175,370],desk_light2:[645,370],
      fan1:[310,310],fan2:[510,310],ac:[420,105],heater:[655,105],
      laptop1:[197,442],laptop2:[622,442],kettle:[420,445]},
    security: {light1:[285,170],light2:[535,170],fan:[420,235],ac:[420,105],
      computer:[285,340],monitor:[490,340],camera:[655,105],kettle:[650,440]},
  };

  function deviceIcon(kind) {
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${iconPaths[kind] || iconPaths.computer}</svg>`;
  }
  function modelLabel(name) {
    if (name.length <= 16) return escape(name);
    const words = name.split(' ');
    const middle = Math.ceil(words.length/2);
    return `<tspan x="0">${escape(words.slice(0,middle).join(' '))}</tspan><tspan x="0" dy="18">${escape(words.slice(middle).join(' '))}</tspan>`;
  }
  function desk(x,y,width=96) {
    return `<g transform="translate(${x} ${y})"><rect width="${width}" height="42" rx="4" fill="#ead9bc" stroke="#bda780" stroke-width="1.5"/><path d="M7 8h${width-14}" stroke="#f9f2e6" stroke-width="2"/><rect x="12" y="49" width="26" height="19" rx="4" fill="#739a8c" stroke="#567e70" stroke-width="1.2"/><rect x="${width-38}" y="49" width="26" height="19" rx="4" fill="#739a8c" stroke="#567e70" stroke-width="1.2"/></g>`;
  }
  function bed(x,y) {
    return `<g transform="translate(${x} ${y})"><rect width="130" height="172" rx="5" fill="#e4d7c1" stroke="#b9aa90" stroke-width="2"/><rect x="7" y="7" width="116" height="158" rx="4" fill="#f7f5ed"/><rect x="15" y="15" width="100" height="32" rx="6" fill="#fff" stroke="#d7dcce"/><rect x="7" y="57" width="116" height="108" rx="3" fill="#a2b5a6"/><path d="M7 72h116" stroke="#c7d3c6" stroke-width="2"/></g>`;
  }
  function furniture(kind) {
    if (kind === 'classroom') {
      let desks = '';
      for (const y of [220,330,430]) for (const x of [210,390,570]) desks += desk(x,y);
      return `<rect x="305" y="70" width="230" height="24" rx="2" fill="#51766a" stroke="#385a50" stroke-width="2"/><path d="M319 83h70m35 0h92" stroke="#bbd0c4" stroke-width="2"/>${desks}${desk(108,425,95)}`;
    }
    if (kind === 'dormitory') {
      return `${bed(125,160)}${bed(565,160)}${desk(130,420,135)}${desk(555,420,135)}<rect x="354" y="192" width="120" height="97" rx="3" fill="#e6dcc9" stroke="#bcb29c" stroke-width="2"/><path d="M414 192v97" stroke="#bcb29c" stroke-width="1.5"/><path d="M405 232v17m18-17v17" stroke="#9c947e" stroke-width="2"/><rect x="363" y="411" width="114" height="65" rx="5" fill="#ead9bc" stroke="#bda780" stroke-width="1.5"/>`;
    }
    return `<rect x="185" y="297" width="390" height="105" rx="5" fill="#ead9bc" stroke="#bda780" stroke-width="2"/><path d="M200 310h360" stroke="#faf4e9" stroke-width="2"/><rect x="252" y="417" width="64" height="47" rx="7" fill="#739a8c" stroke="#567e70" stroke-width="1.5"/><rect x="457" y="417" width="64" height="47" rx="7" fill="#739a8c" stroke="#567e70" stroke-width="1.5"/><rect x="604" y="226" width="94" height="126" rx="3" fill="#dce4dc" stroke="#acbaae" stroke-width="2"/><path d="M651 226v126m-7-70v18m14-18v18" stroke="#9aa99c" stroke-width="1.5"/><rect x="605" y="411" width="94" height="62" rx="4" fill="#ead9bc" stroke="#bda780" stroke-width="1.5"/>`;
  }
  function render(room, interactive=false) {
    const gridId = `floor-${room.id}-${interactive?'detail':'preview'}`;
    const controls = room.devices.map(item => {
      const [x,y] = positions[room.kind]?.[item.id] || [item.x,item.y];
      return `<g class="${interactive?'model-control ':''}${item.is_on?'device-on':''}" data-model-device="${escape(item.id)}" ${interactive?`role="button" tabindex="0" aria-label="${escape(item.name)}: ${item.is_on?'đang bật':'đang tắt'}, ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A" aria-pressed="${item.is_on}"`:''} transform="translate(${x} ${y})"><title>${escape(item.name)} · ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A</title><rect class="device-halo" x="-20" y="-20" width="40" height="40" rx="8"/><g class="device-symbol" transform="translate(-12 -12)" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${iconPaths[item.kind] || iconPaths.computer}</g>${interactive?`<text class="model-device-label" y="36">${modelLabel(item.name)}</text>`:''}</g>`;
    }).join('');
    return `<svg viewBox="0 0 820 560" xmlns="http://www.w3.org/2000/svg" ${interactive?'role="group"':'role="img"'} aria-label="Sơ đồ 2D ${escape(room.name)}"><defs><pattern id="${gridId}" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M44 0H0V44" fill="none" stroke="#e6ece7" stroke-width="1"/></pattern></defs><rect x="72" y="62" width="676" height="456" fill="#f7faf7" stroke="#688679" stroke-width="10"/><rect x="77" y="67" width="666" height="446" fill="url(#${gridId})"/><path d="M72 170v124m676-124v124" stroke="#e9f4f4" stroke-width="11"/><path d="M68 170v124m8-124v124m668-124v124m8-124v124" stroke="#86aead" stroke-width="2"/><path d="M620 518h80" stroke="#f7faf7" stroke-width="12"/><path d="M620 518v-75a75 75 0 0 1 75 75" fill="none" stroke="#aab9ae" stroke-width="1.5"/><path d="M620 518v-75" stroke="#688679" stroke-width="3"/>${furniture(room.kind)}${controls}</svg>`;
  }
  function update(container, room, disabled=false) {
    for (const item of room.devices) {
      const node = container.querySelector(`[data-model-device="${item.id}"]`);
      if (!node) continue;
      node.classList.toggle('device-on',item.is_on);
      if (node.hasAttribute('role')) {
        node.setAttribute('aria-pressed',String(item.is_on));
        node.setAttribute('aria-label',`${item.name}: ${item.is_on?'đang bật':'đang tắt'}, ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A`);
        node.setAttribute('aria-disabled',String(disabled));
      }
      node.querySelector('title').textContent = `${item.name} · ${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:6}).format(item.current_a)} A`;
    }
  }
  window.RoomModel = {render,update,deviceIcon,escape};
})();
