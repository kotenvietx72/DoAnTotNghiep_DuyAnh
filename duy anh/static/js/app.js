/* Một bản chụp từ máy chủ là nguồn dữ liệu chung cho mọi màn hình. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  // Chữ mô tả phụ đã được lược khỏi UI; cập nhật vẫn an toàn khi phần tử vắng mặt.
  const setText = (id,value) => { const element = $(id); if (element) element.textContent = value; };
  const page = document.body.dataset.page;
  const roomId = document.body.dataset.room;
  const esc = window.RoomModel.escape;
  const pendingDevices = new Set();
  const statusNames = {Safe:'An toàn', Warning:'Cảnh báo', Danger:'Nguy hiểm'};
  const statusClass = {Safe:'safe', Warning:'warning', Danger:'danger'};
  const roomCharts = {};
  let state = null, lastRevision = -1, lastSampleRevision = -1;
  let settingsRendered = false, settingsDirty = false;
  let currentChart = null, voltageChart = null, globalReportData = null;
  let aggregateCurrentChart = null, online = false, pollTimer = null;
  const nf = new Intl.NumberFormat('vi-VN', {maximumFractionDigits:1});
  const num = (value, digits=1) => new Intl.NumberFormat('vi-VN', {maximumFractionDigits:digits}).format(value);
  const color = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const roomColors = [color('--green'), color('--amber'), color('--purple')];

  function toast(message, type='success') {
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.textContent = message;
    $('toastRegion').append(item);
    setTimeout(() => item.remove(), 5000);
  }
  async function api(url, options={}) {
    const response = await fetch(url, {cache:'no-store', ...options});
    let data;
    try { data = await response.json(); }
    catch { throw new Error('Máy chủ trả về dữ liệu không hợp lệ. Vui lòng thử lại.'); }
    if (!response.ok || data.success === false) throw new Error(data.error || 'Không thực hiện được yêu cầu.');
    return data;
  }
  const jsonOptions = (method, data) => ({method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  function setConnection(value) {
    online = value;
    $('connectionStatus').className = `connection ${value?'':'offline'}`;
    $('connectionStatus').innerHTML = `<span class="online-dot"></span>${value?'Đã kết nối':'Đang kết nối lại'}`;
    if (state && roomId) renderRoom(state.rooms[roomId]);
  }
  function chartOptions() {
    return {responsive:true, maintainAspectRatio:false, animation:false,
      interaction:{mode:'index', intersect:false},
      plugins:{legend:{display:false}, tooltip:{backgroundColor:color('--ink'), padding:10}},
      scales:{x:{grid:{display:false}, ticks:{color:'#94a18e', maxTicksLimit:6, font:{size:9}}, border:{display:false}},
        y:{beginAtZero:true, grid:{color:'#edf1e9'}, border:{display:false}, ticks:{color:'#94a18e', maxTicksLimit:5, font:{size:9}}}},
    };
  }
  function createSingleChart(canvasId, labelText, borderColor, bgColor, maxY, stepY) {
    const canvas = $(canvasId);
    if (!canvas) return null;
    if (!window.Chart) {
      canvas.parentElement.innerHTML = '<p class="chart-unavailable">Không tải được thư viện biểu đồ. Vui lòng tải lại trang.</p>';
      return null;
    }
    const options = chartOptions();
    if (maxY) options.scales.y.suggestedMax = maxY;
    return new Chart(canvas, {type:'line', data:{labels:[], datasets:[{
      label:labelText, data:[], borderColor, backgroundColor:bgColor || 'transparent',
      borderWidth:2, tension:.25, pointRadius:0, pointHitRadius:8, fill:false,
    }]}, options});
  }
  function initCharts() {
    if (page === 'dashboard') {
      aggregateCurrentChart = createSingleChart('aggregateCurrentChart','Phòng học',roomColors[0],null,10);
      if (aggregateCurrentChart) {
        aggregateCurrentChart.data.datasets = ['Phòng học','Kí túc xá','Phòng bảo vệ'].map((name,index) => ({
          label:name,data:[],borderColor:roomColors[index],borderWidth:2,tension:.25,pointRadius:0,pointHitRadius:8,
        }));
        aggregateCurrentChart.options.plugins.legend = {display:true, position:'bottom',align:'start',labels:{usePointStyle:true,pointStyle:'circle',boxWidth:5,boxHeight:5,padding:18,color:'#7b8d76',font:{size:9}}};
      }
      for (const key of ['r1','r2','r3']) {
        roomCharts[`${key}_i`] = createSingleChart(`${key}CurrentChart`,'Dòng điện (A)',color('--red'));
        roomCharts[`${key}_u`] = createSingleChart(`${key}VoltageChart`,'Điện áp (V)',color('--green'),null,250);
      }
      document.querySelectorAll('.room-chart-pair').forEach(details => details.addEventListener('toggle', () => {
        if (details.open) for (const chart of Object.values(roomCharts)) chart?.resize();
      }));
    } else if (roomId) {
      roomCharts.detail_i = createSingleChart('detailCurrentChart','Dòng điện (A)',color('--red'));
      roomCharts.detail_u = createSingleChart('detailVoltageChart','Điện áp (V)',color('--green'),null,250);
    } else if (page === 'internal') {
      currentChart = createSingleChart('currentChart','Dòng điện (A)',color('--red'));
      voltageChart = createSingleChart('voltageChart','Điện áp (V)',color('--green'),null,250);
    }
  }
  function renderCards(rooms) {
    const holder = $('roomCards');
    if (!holder || holder.children.length) return;
    holder.innerHTML = Object.values(rooms).map(room => `<article class="room-card" data-room="${room.id}">
      <div class="room-card-heading"><h3>${esc(room.name)}</h3><span id="${room.id}-box" class="status-badge safe">An toàn</span></div>
      <div class="room-preview"><div class="room-model" id="${room.id}-model">${RoomModel.render(room)}</div></div>
      <div class="room-card-metrics"><div><small>Dòng điện</small><strong id="${room.id}-i">0 <em>A</em></strong></div><div><small>Điện áp</small><strong id="${room.id}-u">220 <em>V</em></strong></div></div>
      <div class="room-card-load"><div><span id="${room.id}-active">0 thiết bị đang bật</span><span id="${room.id}-load">0% tải</span></div><div class="load-track"><span id="${room.id}-bar" style="width:0%"></span></div></div>
      <a class="room-detail-link" href="/rooms/${room.id}">Chi tiết ${esc(room.name.toLocaleLowerCase('vi-VN'))}</a>
      <details class="room-chart-pair"><summary>Biểu đồ dòng điện & điện áp</summary><div class="mini-chart"><canvas id="${room.id}CurrentChart"></canvas></div><div class="mini-chart"><canvas id="${room.id}VoltageChart"></canvas></div><p class="chart-hint" id="${room.id}-adv" hidden></p></details></article>`).join('');
    initCharts();
  }
  function updateRoomPanel(roomKey, data, timestamp) {
    const badge = $(`${roomKey}-box`);
    if (!badge) return;
    badge.className = `status-badge ${statusClass[data.status]}`;
    badge.textContent = statusNames[data.status];
    $(`${roomKey}-i`).innerHTML = `${num(data.current,3)} <em>A</em>`;
    $(`${roomKey}-u`).innerHTML = `${num(data.voltage)} <em>V</em>`;
    $(`${roomKey}-active`).textContent = `${data.active_count}/${data.devices.length} thiết bị đang bật`;
    const load = data.current / data.thresh_danger * 100;
    $(`${roomKey}-load`).textContent = `${num(load,0)}% tải`;
    const bar = $(`${roomKey}-bar`);
    bar.style.width = `${Math.min(load,100)}%`;
    bar.className = statusClass[data.status];
    $(`${roomKey}-adv`).textContent = data.advice;
    $(`${roomKey}-adv`).hidden = data.status === 'Safe';
    RoomModel.update($(`${roomKey}-model`), data);
  }
  function renderDashboard(data) {
    renderCards(data.rooms);
    const rooms = Object.values(data.rooms);
    const active = rooms.reduce((sum,room) => sum+room.active_count,0);
    const count = rooms.reduce((sum,room) => sum+room.devices.length,0);
    $('totalCurrent').textContent = num(data.total_current,3);
    setText('currentSummary',data.mode === 'legacy' ? 'Dữ liệu kịch bản tự động' : active ? `${active} thiết bị đang sử dụng điện` : 'Chưa có thiết bị đang bật');
    $('activeDevices').textContent = active;
    $('deviceCount').textContent = `/ ${count} thiết bị`;
    const alerts = rooms.filter(room => room.status !== 'Safe');
    $('alertRooms').innerHTML = `${alerts.length} <small>phòng</small>`;
    setText('alertSummary',alerts.length ? alerts.map(room => room.name).join(' · ') : 'Các phòng đang trong giới hạn an toàn');
    setText('lastUpdated',`Cập nhật lúc ${data.timestamp}`);
    $('btnStart').disabled = data.is_simulating;
    $('btnStop').disabled = !data.is_simulating;
    $('simulationMode').value = data.mode;
    $('simulationMode').disabled = data.is_simulating;
    $('monitorIndicator').classList.toggle('running',data.is_simulating);
    $('monitorLabel').textContent = data.is_simulating ? 'Đang lấy mẫu thời gian thực' : 'Sẵn sàng giám sát';
    setText('monitorDescription',data.is_simulating ? 'Dữ liệu được ghi nhận mỗi giây, đồng bộ mọi trình duyệt.' : 'Công tắc vẫn cập nhật tải; khởi động để ghi lịch sử.');
    setText('chartHint',data.is_simulating ? 'Đang ghi nhận dữ liệu theo từng giây.' : 'Khởi động lấy mẫu để ghi nhận biểu đồ theo thời gian.');
    for (const room of rooms) updateRoomPanel(room.id,room,data.timestamp);
  }
  function renderRoom(room) {
    if (!room) return;
    $('roomCurrent').textContent = num(room.current,3);
    $('roomVoltage').textContent = num(room.voltage);
    $('roomActive').textContent = room.active_count;
    $('roomTotal').textContent = `/ ${room.devices.length} thiết bị`;
    $('roomStatus').className = `status-badge ${statusClass[room.status]}`;
    $('roomStatus').textContent = statusNames[room.status];
    const load = room.current / room.thresh_danger * 100;
    $('roomLoadText').textContent = `${num(load,0)}%`;
    $('roomLoadBar').style.width = `${Math.min(load,100)}%`;
    $('roomLoadBar').className = statusClass[room.status];
    $('roomWarnThreshold').textContent = `Cảnh báo: ${num(room.thresh_warn,2)} A`;
    $('roomDangerThreshold').textContent = `Nguy hiểm: ${num(room.thresh_danger,2)} A`;
    $('roomAdvice').textContent = room.advice;
    $('roomAdvice').className = `room-advice ${statusClass[room.status]}`;
    $('roomAdvice').hidden = room.status === 'Safe';
    const model = $('roomModel');
    if (!model.children.length) model.innerHTML = RoomModel.render(room,true);
    const list = $('deviceList');
    if (!list.children.length) {
      list.innerHTML = room.devices.map(item => `<div class="device-row" id="row-${item.id}"><span class="device-type-icon">${RoomModel.deviceIcon(item.kind)}</span><div class="device-info"><strong>${esc(item.name)}</strong><small id="info-${item.id}"></small></div><button type="button" role="switch" aria-checked="false" aria-label="${esc(item.name)}" class="switch" data-device="${item.id}"></button></div>`).join('');
    }
    const disabled = !online || state?.mode !== 'devices';
    for (const item of room.devices) {
      const pending = pendingDevices.has(item.id);
      $(`row-${item.id}`).classList.toggle('is-on',item.is_on);
      $(`info-${item.id}`).textContent = `${num(item.current_a,3)} A · ${pending?'Đang cập nhật…':item.is_on?'Đang bật':'Đang tắt'}`;
      const control = list.querySelector(`[data-device="${item.id}"]`);
      control.setAttribute('aria-checked',String(item.is_on));
      control.disabled = disabled || pending;
    }
    RoomModel.update(model,room,disabled);
  }
  async function toggleDevice(deviceId) {
    if (!state || pendingDevices.has(deviceId) || !online) return;
    if (state.mode !== 'devices') return toast('Hãy chuyển sang chế độ Theo thiết bị tại trang Tổng quan.','warning');
    const item = state.rooms[roomId].devices.find(item => item.id === deviceId);
    if (!item) return;
    pendingDevices.add(deviceId);
    renderRoom(state.rooms[roomId]);
    try {
      acceptState(await api(`/api/rooms/${roomId}/devices/${deviceId}`,jsonOptions('POST',{is_on:!item.is_on})));
    } catch (error) { toast(error.message,'error'); }
    finally { pendingDevices.delete(deviceId); renderRoom(state.rooms[roomId]); }
  }
  function renderSettings(rooms) {
    if (settingsRendered) return;
    $('settingsRooms').innerHTML = Object.values(rooms).map(room => `<section class="panel settings-room" data-settings-room="${room.id}"><div class="settings-room-heading"><h2>${esc(room.name)}</h2></div><div class="threshold-fields"><div><label class="field-label" for="${room.id}-warn">Ngưỡng cảnh báo</label><div class="input-unit"><input id="${room.id}-warn" data-field="thresh_warn" type="number" min="0.01" max="1000" step="0.01" value="${room.thresh_warn}" required><span>A</span></div></div><div><label class="field-label" for="${room.id}-danger">Ngưỡng nguy hiểm</label><div class="input-unit"><input id="${room.id}-danger" data-field="thresh_danger" type="number" min="0.01" max="1000" step="0.01" value="${room.thresh_danger}" required><span>A</span></div></div></div><h3 class="settings-device-title">Dòng điện thiết bị</h3><div class="setting-device-grid">${room.devices.map(item => `<div><label class="field-label" for="${room.id}-${item.id}-current">${esc(item.name)}</label><div class="input-unit"><input id="${room.id}-${item.id}-current" data-current-device="${item.id}" type="number" min="0" max="1000" step="any" value="${item.current_a}" required><span>A</span></div></div>`).join('')}</div></section>`).join('');
    settingsRendered = true;
  }
  async function saveSettings(event) {
    event.preventDefault();
    const form = $('settingsForm');
    if (!form.reportValidity()) return;
    const payload = {rooms:{}};
    for (const section of form.querySelectorAll('[data-settings-room]')) {
      const cfg = {devices:{}};
      for (const input of section.querySelectorAll('[data-field]')) cfg[input.dataset.field] = Number(input.value);
      if (cfg.thresh_warn >= cfg.thresh_danger) {
        section.querySelector('[data-field="thresh_danger"]').focus();
        return toast('Ngưỡng nguy hiểm phải lớn hơn ngưỡng cảnh báo.','error');
      }
      for (const input of section.querySelectorAll('[data-current-device]')) cfg.devices[input.dataset.currentDevice] = Number(input.value);
      payload.rooms[section.dataset.settingsRoom] = cfg;
    }
    const buttons = document.querySelectorAll('[form="settingsForm"],#settingsForm button[type="submit"]');
    buttons.forEach(button => button.disabled = true);
    try {
      acceptState(await api('/api/settings',jsonOptions('PUT',payload)));
      settingsDirty = false;
      $('settingsMessage').textContent = `Đã lưu cấu hình lúc ${new Date().toLocaleTimeString('vi-VN')}.`;
      toast('Đã lưu cài đặt. Tải điện và cảnh báo đã được cập nhật.');
    } catch (error) { toast(error.message,'error'); }
    finally { buttons.forEach(button => button.disabled = false); }
  }
  function acceptState(data) {
    if (!data || !data.rooms) return;
    if (data.server_id !== state?.server_id) {
      lastRevision = lastSampleRevision = -1;
      clearCharts();
    }
    if (data.revision <= lastRevision) return;
    const started = state && !state.is_simulating && data.is_simulating;
    state = data;
    lastRevision = data.revision;
    if (started) clearCharts();
    if ($('legacyNotice')) $('legacyNotice').hidden = data.mode !== 'legacy';
    if (page === 'dashboard') renderDashboard(data);
    if (roomId) renderRoom(data.rooms[roomId]);
    if (page === 'settings') renderSettings(data.rooms);
    if (page === 'internal') updateAnalysisThresholds();
  }
  function pushPointToChart(chart,label,value) {
    if (!chart) return;
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(value);
    if (chart.data.labels.length>60) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update('none');
  }
  function clearCharts() {
    for (const chart of [aggregateCurrentChart,...Object.values(roomCharts)]) if (chart) {
      chart.data.labels = [];
      chart.data.datasets.forEach(dataset => dataset.data = []);
      chart.update('none');
    }
  }
  function receiveSample(data) {
    acceptState(data);
    if (!data.is_simulating || data.revision <= lastSampleRevision) return;
    lastSampleRevision = data.revision;
    if (aggregateCurrentChart) {
      aggregateCurrentChart.data.labels.push(data.timestamp);
      Object.values(data.rooms).forEach((room,index) => aggregateCurrentChart.data.datasets[index].data.push(room.current));
      if (aggregateCurrentChart.data.labels.length>60) {
        aggregateCurrentChart.data.labels.shift();
        aggregateCurrentChart.data.datasets.forEach(dataset => dataset.data.shift());
      }
      aggregateCurrentChart.update('none');
    }
    for (const room of Object.values(data.rooms)) {
      pushPointToChart(roomCharts[`${room.id}_i`],data.timestamp,room.current);
      pushPointToChart(roomCharts[`${room.id}_u`],data.timestamp,room.voltage);
    }
    if (roomId) {
      pushPointToChart(roomCharts.detail_i,data.timestamp,data.rooms[roomId].current);
      pushPointToChart(roomCharts.detail_u,data.timestamp,data.rooms[roomId].voltage);
    }
  }
  async function toggleSim(action) {
    try {
      const result = await api('/toggle_simulation',jsonOptions('POST',{action}));
      acceptState(result.state);
      toast(result.message);
    } catch (error) { toast(error.message,'error'); }
  }
  function updateAnalysisThresholds() {
    if (!state || !$('analysisRoom')) return;
    const cfg = state.rooms[$('analysisRoom').value] || {thresh_warn:25,thresh_danger:40};
    $('analysisThresholds').textContent = `Cảnh báo ≥ ${num(cfg.thresh_warn,2)} A · Nguy hiểm ≥ ${num(cfg.thresh_danger,2)} A`;
  }
  async function uploadAndAnalyze(event) {
    event?.preventDefault();
    const file = $('excelFile').files[0];
    if (!file) return toast('Vui lòng chọn file dữ liệu.','warning');
    if (file.size > 10*1024*1024) return toast('File vượt quá giới hạn 10 MB.','error');
    const button = $('analyzeButton');
    button.disabled = true;
    button.textContent = 'Đang phân tích…';
    $('analysisError').textContent = '';
    try {
      const data = await api('/analyze_1phase',{method:'POST',body:new FormData($('analysisForm'))});
      globalReportData = data.report_data;
      $('chartSection').hidden = false;
      for (const [id,key] of [['txtTotal','sample_count'],['txtSafe','safe_count'],['txtWarn','warning_count'],['txtDang','danger_count']]) $(id).textContent = nf.format(globalReportData[key]);
      $('analysisSummary').textContent = `${globalReportData.room_name} · Cảnh báo ≥ ${num(globalReportData.thresh_warn,2)} A · Nguy hiểm ≥ ${num(globalReportData.thresh_danger,2)} A`;
      const log = globalReportData.event_log;
      $('analysisEvents').innerHTML = log.length ? log.map(line=>`<li>${esc(line)}</li>`).join('') : '<li>Không ghi nhận thay đổi trạng thái cảnh báo.</li>';
      for (const [chart,values] of [[currentChart,data.I_val],[voltageChart,data.U_val]]) if (chart) {
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = values;
        chart.resize();
        chart.update('none');
      }
      $('chartSection').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
      toast('Đã phân tích dữ liệu thành công.');
    } catch (error) { $('analysisError').textContent = error.message; }
    finally { button.disabled = false; button.textContent = 'Phân tích dữ liệu'; }
  }
  async function savePdf(element, filename) {
    if (!window.html2pdf) throw new Error('Không tải được thư viện PDF. Vui lòng tải lại trang.');
    await html2pdf().set({margin:[12,12,12,12],filename,
      image:{type:'jpeg',quality:.96},
      // Báo cáo A4 dùng viewport cố định, không phụ thuộc vị trí cuộn/độ rộng điện thoại.
      html2canvas:{scale:2,backgroundColor:'#ffffff',logging:false,
        windowWidth:1024,windowHeight:1440,scrollX:0,scrollY:0},
      jsPDF:{unit:'mm',format:'a4',orientation:'portrait'},pagebreak:{mode:['css','legacy'],avoid:['tr','h2']},
    }).from(element).save();
  }
  async function downloadPDFReport() {
    const button = page === 'internal' ? $('btnDownloadPDF') : $('exportReport');
    if (button) button.disabled = true;
    try {
      const element = document.createElement('div');
      element.className = 'report-document';
      const now = new Date().toLocaleString('vi-VN');
      if (page === 'internal') {
        if (!globalReportData) throw new Error('Vui lòng phân tích dữ liệu trước.');
        const report = globalReportData;
        element.innerHTML = `<h1>BÁO CÁO PHÂN TÍCH NỘI BỘ LƯỚI ĐIỆN HẠ THẾ</h1><p>Thời điểm xuất: ${esc(now)}</p><p>Khu vực: <strong>${esc(report.room_name)}</strong></p><p>Ngưỡng áp dụng: cảnh báo ≥ ${report.thresh_warn} A; nguy hiểm ≥ ${report.thresh_danger} A.</p><h2>1. Tổng quan dữ liệu</h2><table><tr><th>Tổng số mẫu</th><th>Mẫu an toàn</th><th>Đợt cảnh báo</th><th>Đợt nguy hiểm</th></tr><tr><td>${report.sample_count}</td><td>${report.safe_count}</td><td>${report.warning_count}</td><td>${report.danger_count}</td></tr></table><p class="report-note">Thống kê theo số mẫu; tương đương giây chỉ khi chu kỳ lấy mẫu là 1 giây.</p><h2>2. Nhật ký thay đổi trạng thái</h2><ul>${report.event_log.length?report.event_log.map(line=>`<li>${esc(line)}</li>`).join(''):'<li>Không ghi nhận thay đổi trạng thái cảnh báo.</li>'}</ul>`;
        await savePdf(element,'Bao_Cao_Phan_Tich_Noi_Bo_Luoi_Dien.pdf');
      } else {
        const report = await api('/get_report');
        element.innerHTML = `<h1>BÁO CÁO GIÁM SÁT QUÁ TẢI LƯỚI ĐIỆN HẠ THẾ</h1><p>Thời điểm xuất: ${esc(now)}</p><p>Chế độ: ${report.mode==='devices'?'Theo thiết bị':'Kịch bản tự động'}. Thời gian ghi nhận: ${num(report.total_runtime,2)} giây.</p><h2>1. Thống kê theo phòng</h2><table><thead><tr><th>Khu vực</th><th>Cảnh báo / nguy hiểm (A)</th><th>An toàn (s)</th><th>Cảnh báo (s)</th><th>Nguy hiểm (s)</th></tr></thead><tbody>${Object.entries(report.configs).map(([key,cfg])=>`<tr><td>${esc(cfg.name)}</td><td>${cfg.thresh_warn} / ${cfg.thresh_danger}</td><td>${num(report.rooms[key].safe,2)}</td><td>${num(report.rooms[key].warn,2)}</td><td>${num(report.rooms[key].danger,2)}</td></tr>`).join('')}</tbody></table><p class="report-note">Ngưỡng trong bảng là cấu hình hiện tại. Các thay đổi cấu hình trong phiên được ghi trong nhật ký; thời lượng được phân loại theo ngưỡng có hiệu lực tại thời điểm ghi nhận.</p><h2>2. Phụ tải tại thời điểm xuất</h2><table><tr><th>Khu vực</th><th>Thiết bị bật</th><th>Dòng điện (A)</th><th>Điện áp (V)</th><th>Trạng thái</th></tr>${Object.values(report.state.rooms).map(room=>`<tr><td>${esc(room.name)}</td><td>${room.active_count}/${room.devices.length}</td><td>${num(room.current,3)}</td><td>${num(room.voltage)}</td><td>${statusNames[room.status]}</td></tr>`).join('')}</table><h2>3. Nhật ký vận hành</h2><ul>${report.event_log.length?report.event_log.map(line=>`<li>${esc(line)}</li>`).join(''):'<li>Chưa ghi nhận sự kiện cảnh báo trong phiên.</li>'}</ul>`;
        await savePdf(element,'Bao_Cao_Giam_Sat_3_Phong.pdf');
      }
      toast('Đã tạo báo cáo PDF.');
    } catch (error) { toast(error.message,'error'); }
    finally { if (button) button.disabled = false; }
  }

  $('todayDate').textContent = new Date().toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric'});
  if (page !== 'dashboard') initCharts();
  $('btnStart')?.addEventListener('click',()=>toggleSim('start'));
  $('btnStop')?.addEventListener('click',()=>toggleSim('stop'));
  $('simulationMode')?.addEventListener('change',async event=>{
    try { acceptState(await api('/api/mode',jsonOptions('POST',{mode:event.target.value}))); }
    catch (error) { event.target.value = state.mode; toast(error.message,'error'); }
  });
  $('exportReport')?.addEventListener('click',downloadPDFReport);
  $('btnDownloadPDF')?.addEventListener('click',downloadPDFReport);
  $('settingsForm')?.addEventListener('submit',saveSettings);
  $('settingsForm')?.addEventListener('input',()=>{ settingsDirty = true; $('settingsMessage').textContent = 'Có thay đổi chưa được lưu.'; });
  $('analysisForm')?.addEventListener('submit',uploadAndAnalyze);
  $('analysisRoom')?.addEventListener('change',updateAnalysisThresholds);
  $('deviceList')?.addEventListener('click',event=>{
    const control = event.target.closest('[data-device]');
    if (control) toggleDevice(control.dataset.device);
  });
  function modelAction(event) {
    const control = event.target.closest('[data-model-device]');
    if (control) toggleDevice(control.dataset.modelDevice);
  }
  $('roomModel')?.addEventListener('click',modelAction);
  $('roomModel')?.addEventListener('keydown',event=>{
    if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); modelAction(event);}
  });
  async function refresh() {
    try {
      const data = await api('/api/state');
      setConnection(true);
      acceptState(data);
      if (pollTimer && data.is_simulating) receiveSample(data);
    } catch (error) { setConnection(false); if (!state) toast(error.message,'error'); }
  }
  if (window.io) {
    const socket = io({reconnection:true});
    socket.on('connect',()=>{setConnection(true); refresh();});
    socket.on('disconnect',()=>setConnection(false));
    socket.on('connect_error',()=>setConnection(false));
    socket.on('state_update',acceptState);
    socket.on('new_sensor_data',receiveSample);
  } else {
    pollTimer = setInterval(refresh,1000);
  }
  refresh();
})();
