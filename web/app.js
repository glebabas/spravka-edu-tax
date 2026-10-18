/**
 * Логика веб-приложения SpravkaEduTax
 */

// Профили по умолчанию
const PROFILES = {
  burlakov: {
    profile_name: "ИП Бурлаков Никита Сергеевич",
    org_inn: "773610841807",
    org_kpp: "",
    org_name_lines: [
      "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ",
      "БУРЛАКОВ НИКИТА СЕРГЕЕВИЧ",
      "",
      ""
    ],
    full_time: 0,
    confirm_last_name: "БУРЛАКОВ",
    confirm_first_name: "НИКИТА",
    confirm_middle_name: "СЕРГЕЕВИЧ",
    signature_path: "/assets/signature.png",
    default_doc_code: "21",
    default_year: 2025,
    last_number: 34
  },
  clean: {
    profile_name: "Чистый шаблон (для GitHub)",
    org_inn: "",
    org_kpp: "",
    org_name_lines: ["", "", "", ""],
    full_time: 0,
    confirm_last_name: "",
    confirm_first_name: "",
    confirm_middle_name: "",
    signature_path: "",
    default_doc_code: "21",
    default_year: 2026,
    last_number: 0
  }
};

let currentConfig = { ...PROFILES.burlakov };
let currentPdfBlob = null;
let currentPdfUrl = null;

// Инициализация при загрузке страницы
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupFormMasks();
  setupSignaturePad();
  setupBatchUpload();

  // Попытка загрузить конфигурацию с сервера или из localStorage
  await loadConfiguration();
  applyConfigToSettingsForm();

  // Заполнение даты по умолчанию
  const today = new Date();
  const defDate = `${String(today.getDate()).padStart(2, '0')}.${String(today.getMonth() + 1).padStart(2, '0')}.${today.getFullYear()}`;
  const docDateInput = document.getElementById("docDate");
  if (docDateInput && !docDateInput.value) {
    docDateInput.value = defDate;
  }

  // Заполнение тестовыми данными для мгновенного теста (Симонова)
  fillDemoData();

  // Обработчик профиля
  document.getElementById("profileSelect").addEventListener("change", (e) => {
    switchProfile(e.target.value);
  });

  // Кнопка следующего номера (+1)
  document.getElementById("btnNextNumber").addEventListener("click", () => {
    const numInput = document.getElementById("docNumber");
    let val = parseInt(numInput.value, 10);
    if (isNaN(val)) val = currentConfig.last_number || 0;
    val += 1;
    numInput.value = String(val).padStart(3, '0');
  });

  // Переключатель "Одно лицо"
  document.getElementById("isSamePerson").addEventListener("change", (e) => {
    const studentBlock = document.getElementById("studentDetailsBlock");
    if (e.target.checked) {
      studentBlock.classList.add("hidden");
    } else {
      studentBlock.classList.remove("hidden");
    }
  });

  // Отправка формы одиночной генерации
  document.getElementById("spravkaForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    await generateSingleSpravka();
  });

  // Кнопка "Скачать файл"
  document.getElementById("btnDownload").addEventListener("click", () => {
    if (!currentPdfBlob) {
      alert("Сначала сформируйте PDF справки!");
      return;
    }
    const docNum = document.getElementById("docNumber").value || "справка";
    const lastName = document.getElementById("payerLastName").value || "клиент";
    const filename = `${docNum}_${lastName}_справка.pdf`;
    downloadBlob(currentPdfBlob, filename);
  });

  // Кнопка "Печать"
  document.getElementById("btnPrint").addEventListener("click", () => {
    const frame = document.getElementById("pdfPreviewFrame");
    if (frame && frame.contentWindow) {
      frame.contentWindow.focus();
      frame.contentWindow.print();
    } else {
      alert("Сначала сформируйте PDF для печати!");
    }
  });

  // Кнопка "Очистить"
  document.getElementById("btnReset").addEventListener("click", () => {
    document.getElementById("payerLastName").value = "";
    document.getElementById("payerFirstName").value = "";
    document.getElementById("payerMiddleName").value = "";
    document.getElementById("payerBirthDate").value = "";
    document.getElementById("payerInn").value = "";
    document.getElementById("docPassport").value = "";
    document.getElementById("docIssueDate").value = "";
    document.getElementById("amountRub").value = "";
  });

  // Сохранение настроек организации
  document.getElementById("btnSaveSettings").addEventListener("click", saveSettings);
});

// Настройка переключения вкладок
function setupTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const targetId = `tab-${tab.dataset.tab}`;
      document.querySelectorAll(".tab-pane").forEach((pane) => {
        pane.classList.remove("active");
      });
      document.getElementById(targetId).classList.add("active");
    });
  });
}

// Загрузка конфигурации
async function loadConfiguration() {
  try {
    const resp = await fetch("/api/config");
    if (resp.ok) {
      const serverCfg = await resp.json();
      currentConfig = { ...currentConfig, ...serverCfg };
      return;
    }
  } catch (e) {
    console.log("Сервер недоступен, работа в автономном режиме");
  }

  const localSaved = localStorage.getItem("spravka_config_custom");
  if (localSaved) {
    try {
      currentConfig = JSON.parse(localSaved);
    } catch (e) {}
  }
}

// Применение настроек к форме вкладки 3
function applyConfigToSettingsForm() {
  document.getElementById("orgInn").value = currentConfig.org_inn || "";
  document.getElementById("orgKpp").value = currentConfig.org_kpp || "";
  const lines = currentConfig.org_name_lines || ["", "", "", ""];
  document.getElementById("orgLine1").value = lines[0] || "";
  document.getElementById("orgLine2").value = lines[1] || "";
  document.getElementById("orgLine3").value = lines[2] || "";
  document.getElementById("orgLine4").value = lines[3] || "";
  document.getElementById("fullTimeSelect").value = String(currentConfig.full_time ?? 0);
  document.getElementById("defYear").value = currentConfig.default_year || 2025;
  document.getElementById("confirmLastName").value = currentConfig.confirm_last_name || "";
  document.getElementById("confirmFirstName").value = currentConfig.confirm_first_name || "";
  document.getElementById("confirmMiddleName").value = currentConfig.confirm_middle_name || "";
  document.getElementById("docYear").value = currentConfig.default_year || 2025;

  if (currentConfig.last_number) {
    document.getElementById("docNumber").value = String(currentConfig.last_number + 1).padStart(3, '0');
  }
}

// Переключение профиля
function switchProfile(profileKey) {
  if (profileKey === "burlakov") {
    currentConfig = { ...PROFILES.burlakov };
  } else if (profileKey === "clean") {
    currentConfig = { ...PROFILES.clean };
  } else {
    const saved = localStorage.getItem("spravka_config_custom");
    if (saved) {
      try {
        currentConfig = JSON.parse(saved);
      } catch (e) {}
    }
  }
  applyConfigToSettingsForm();
}

// Сохранение настроек
async function saveSettings() {
  const lines = [
    document.getElementById("orgLine1").value.trim().toUpperCase(),
    document.getElementById("orgLine2").value.trim().toUpperCase(),
    document.getElementById("orgLine3").value.trim().toUpperCase(),
    document.getElementById("orgLine4").value.trim().toUpperCase()
  ];

  currentConfig.org_inn = document.getElementById("orgInn").value.trim();
  currentConfig.org_kpp = document.getElementById("orgKpp").value.trim();
  currentConfig.org_name_lines = lines;
  currentConfig.full_time = parseInt(document.getElementById("fullTimeSelect").value, 10);
  currentConfig.default_year = parseInt(document.getElementById("defYear").value, 10);
  currentConfig.confirm_last_name = document.getElementById("confirmLastName").value.trim().toUpperCase();
  currentConfig.confirm_first_name = document.getElementById("confirmFirstName").value.trim().toUpperCase();
  currentConfig.confirm_middle_name = document.getElementById("confirmMiddleName").value.trim().toUpperCase();

  localStorage.setItem("spravka_config_custom", JSON.stringify(currentConfig));

  // Попытка отправить на сервер
  try {
    const resp = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentConfig)
    });
    if (resp.ok) {
      alert("✓ Настройки успешно сохранены!");
      return;
    }
  } catch (e) {}

  alert("✓ Настройки сохранены в браузере!");
}

// Умные маски ввода
function setupFormMasks() {
  // Маска для паспорта (ХХХХ ХХХХХХ)
  const passportInputs = [document.getElementById("docPassport"), document.getElementById("stPassport")];
  passportInputs.forEach((input) => {
    if (!input) return;
    input.addEventListener("input", (e) => {
      let v = e.target.value.replace(/[^0-9]/g, "");
      if (v.length > 4) {
        v = v.slice(0, 4) + " " + v.slice(4, 10);
      }
      e.target.value = v;
    });
  });

  // Маска для дат (ДД.ММ.ГГГГ)
  const dateInputs = [
    document.getElementById("docDate"),
    document.getElementById("payerBirthDate"),
    document.getElementById("docIssueDate"),
    document.getElementById("stBirthDate"),
    document.getElementById("stIssueDate")
  ];
  dateInputs.forEach((input) => {
    if (!input) return;
    input.addEventListener("input", (e) => {
      let v = e.target.value.replace(/[^0-9]/g, "");
      if (v.length > 8) v = v.slice(0, 8);
      if (v.length > 4) {
        v = v.slice(0, 2) + "." + v.slice(2, 4) + "." + v.slice(4);
      } else if (v.length > 2) {
        v = v.slice(0, 2) + "." + v.slice(2);
      }
      e.target.value = v;
    });
  });

  // Автокапс для ФИО
  document.querySelectorAll(".uppercase-input").forEach((input) => {
    input.addEventListener("input", (e) => {
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      e.target.value = e.target.value.toUpperCase();
      e.target.setSelectionRange(start, end);
    });
  });

  // Разделитель тысяч для суммы
  const amountInput = document.getElementById("amountRub");
  if (amountInput) {
    amountInput.addEventListener("input", (e) => {
      let v = e.target.value.replace(/[^0-9]/g, "");
      if (v) {
        e.target.value = Number(v).toLocaleString("ru-RU");
      }
    });
  }
}

// Заполнение демо-данными (как в примере 031 Симонова)
function fillDemoData() {
  document.getElementById("payerLastName").value = "СИМОНОВА";
  document.getElementById("payerFirstName").value = "НИНА";
  document.getElementById("payerMiddleName").value = "АНАТОЛЬЕВНА";
  document.getElementById("payerBirthDate").value = "03.07.1958";
  document.getElementById("docPassport").value = "4506 765502";
  document.getElementById("docIssueDate").value = "13.01.2004";
  document.getElementById("amountRub").value = "139 758";
  document.getElementById("amountKop").value = "0";
  document.getElementById("docNumber").value = "031";
  document.getElementById("docDate").value = "07.06.2026";
}

// Генерация одиночной справки
async function generateSingleSpravka() {
  const btn = document.getElementById("btnGenerate");
  const origText = btn.innerHTML;
  btn.innerHTML = "⏳ Формирование...";
  btn.disabled = true;

  try {
    const rawPassport = document.getElementById("docPassport").value.replace(/[^0-9]/g, "");
    const docSeries = rawPassport.slice(0, 4);
    const docNum = rawPassport.slice(4);

    const rawStPassport = (document.getElementById("stPassport").value || "").replace(/[^0-9]/g, "");
    const stDocSeries = rawStPassport.slice(0, 4);
    const stDocNum = rawStPassport.slice(4);

    const rubStr = document.getElementById("amountRub").value.replace(/[^0-9]/g, "");

    const payload = {
      // Статические реквизиты
      org_inn: currentConfig.org_inn,
      org_kpp: currentConfig.org_kpp,
      org_name_lines: currentConfig.org_name_lines,
      full_time: currentConfig.full_time,
      confirm_last_name: currentConfig.confirm_last_name,
      confirm_first_name: currentConfig.confirm_first_name,
      confirm_middle_name: currentConfig.confirm_middle_name,
      signature_path: document.getElementById("enableSignature").checked ? currentConfig.signature_path : null,

      // Документ
      doc_number: document.getElementById("docNumber").value.trim(),
      correction_num: parseInt(document.getElementById("correctionNum").value, 10) || 0,
      year: parseInt(document.getElementById("docYear").value, 10) || 2025,
      doc_date: document.getElementById("docDate").value.trim(),

      // Плательщик
      payer_last_name: document.getElementById("payerLastName").value.trim().toUpperCase(),
      payer_first_name: document.getElementById("payerFirstName").value.trim().toUpperCase(),
      payer_middle_name: document.getElementById("payerMiddleName").value.trim().toUpperCase(),
      payer_inn: document.getElementById("payerInn").value.trim(),
      payer_birth_date: document.getElementById("payerBirthDate").value.trim(),
      doc_code: document.getElementById("docCode").value,
      doc_series: docSeries,
      doc_num: docNum,
      doc_issue_date: document.getElementById("docIssueDate").value.trim(),

      // Сумма
      amount_rub: parseInt(rubStr, 10) || 0,
      amount_kop: parseInt(document.getElementById("amountKop").value, 10) || 0,

      // Одно лицо
      is_same_person: document.getElementById("isSamePerson").checked ? 1 : 0,
      has_page_2: true,

      // Обучаемый (если отличается)
      student_last_name: document.getElementById("stLastName").value.trim().toUpperCase(),
      student_first_name: document.getElementById("stFirstName").value.trim().toUpperCase(),
      student_middle_name: document.getElementById("stMiddleName").value.trim().toUpperCase(),
      student_birth_date: document.getElementById("stBirthDate").value.trim(),
      student_doc_code: document.getElementById("docCode").value,
      student_doc_series: stDocSeries,
      student_doc_num: stDocNum,
      student_doc_issue_date: document.getElementById("stIssueDate").value.trim()
    };

    // 1. Попытка сгенерировать через локальный бэкенд (Python)
    let pdfBlob = null;
    try {
      const resp = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        pdfBlob = await resp.blob();
      }
    } catch (err) {
      console.log("Локальный бэкенд недоступен, выполняем генерацию в браузере:", err);
    }

    // 2. Fallback: Генерация прямо в браузере через pdf-lib
    if (!pdfBlob) {
      pdfBlob = await generatePdfInBrowser(payload);
    }

    if (pdfBlob) {
      currentPdfBlob = pdfBlob;
      if (currentPdfUrl) URL.revokeObjectURL(currentPdfUrl);
      currentPdfUrl = URL.createObjectURL(pdfBlob);

      const frame = document.getElementById("pdfPreviewFrame");
      frame.src = currentPdfUrl;
      document.getElementById("previewPlaceholder").style.display = "none";
      frame.style.display = "block";
    }
  } catch (err) {
    alert("Ошибка генерации: " + err.message);
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

// Автономная генерация в браузере через PDF-lib (если нет Python бэкенда)
async function generatePdfInBrowser(data) {
  if (typeof PDFLib === "undefined") {
    throw new Error("Библиотека PDF-Lib не загружена");
  }

  // Загрузка шаблона
  const tplResp = await fetch("/assets/example.pdf");
  if (!tplResp.ok) throw new Error("Не удалось загрузить бланк example.pdf");
  const tplBytes = await tplResp.arrayBuffer();

  const pdfDoc = await PDFLib.PDFDocument.load(tplBytes);
  const helveticaFont = await pdfDoc.embedFont(PDFLib.StandardFonts.Helvetica);

  const pages = pdfDoc.getPages();
  const page1 = pages[0];
  const p1Height = page1.getHeight();

  const CELL_SIZE = 14.17323;

  function drawCells(page, text, startX, yTop, fontSize = 11) {
    if (!text) return;
    const yBaseline = p1Height - yTop - 9;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (ch === ' ') continue;
      const cellX = startX + i * CELL_SIZE;
      const w = helveticaFont.widthOfTextAtSize(ch, fontSize);
      page.drawText(ch, {
        x: cellX + (CELL_SIZE - w) / 2,
        y: yBaseline,
        size: fontSize,
        font: helveticaFont,
        color: PDFLib.rgb(0, 0, 0)
      });
    }
  }

  function drawDate(page, dateStr, startX, yTop) {
    const clean = dateStr.replace(/[^0-9]/g, '');
    if (clean.length !== 8) return;
    const idxs = [0, 1, 3, 4, 6, 7, 8, 9];
    const yBaseline = p1Height - yTop - 9;
    for (let i = 0; i < clean.length; i++) {
      const ch = clean[i];
      const cellX = startX + idxs[i] * CELL_SIZE;
      const w = helveticaFont.widthOfTextAtSize(ch, 11);
      page.drawText(ch, {
        x: cellX + (CELL_SIZE - w) / 2,
        y: yBaseline,
        size: 11,
        font: helveticaFont,
        color: PDFLib.rgb(0, 0, 0)
      });
    }
  }

  // Заполнение стр. 1
  drawCells(page1, data.org_inn, 198.42, 16.56);
  drawCells(page1, data.doc_number, 85.03, 131.86);
  drawCells(page1, String(data.correction_num), 382.67, 131.86);
  drawCells(page1, String(data.year), 524.40, 131.86);

  const orgYs = [175.76, 198.46, 221.16, 243.86];
  (data.org_name_lines || []).forEach((line, idx) => {
    if (idx < 4 && line) drawCells(page1, line.toUpperCase(), 14.17, orgYs[idx]);
  });

  drawCells(page1, String(data.full_time), 240.94, 285.50);
  drawCells(page1, data.payer_last_name, 70.86, 326.96);
  drawCells(page1, data.payer_first_name, 70.86, 352.46);
  drawCells(page1, data.payer_middle_name, 70.86, 378.06);
  if (data.payer_birth_date) drawDate(page1, data.payer_birth_date, 368.50, 403.56);

  drawCells(page1, data.doc_code || '21', 113.38, 448.90);
  const sn = `${data.doc_series} ${data.doc_num}`.trim();
  drawCells(page1, sn, 297.63, 448.90);
  if (data.doc_issue_date) drawDate(page1, data.doc_issue_date, 113.38, 474.40);

  drawCells(page1, String(data.is_same_person), 269.29, 499.90);

  // Сумма
  const rubStr = String(data.amount_rub || 0);
  const dotCellX = 453.54;
  const yAmountBase = p1Height - 528.66 - 9;
  for (let i = 0; i < rubStr.length; i++) {
    const ch = rubStr[rubStr.length - 1 - i];
    const cellX = dotCellX - (i + 1) * CELL_SIZE;
    const w = helveticaFont.widthOfTextAtSize(ch, 11);
    page1.drawText(ch, { x: cellX + (CELL_SIZE - w) / 2, y: yAmountBase, size: 11, font: helveticaFont });
  }
  const kopStr = String(data.amount_kop || 0).padStart(2, '0');
  drawCells(page1, kopStr, dotCellX + CELL_SIZE, 528.66);

  drawCells(page1, data.confirm_last_name, 14.17, 588.56);
  drawCells(page1, data.confirm_first_name, 14.17, 611.26);
  drawCells(page1, data.confirm_middle_name, 14.17, 633.96);
  if (data.doc_date) drawDate(page1, data.doc_date, 161.29, 674.36);
  drawCells(page1, "002", 127.55, 704.16);

  // Заполнение стр. 2
  if (pages.length > 1) {
    const page2 = pages[1];
    drawCells(page2, data.org_inn, 184.25, 16.56);
    const stLast = (data.student_last_name || data.payer_last_name).toUpperCase();
    const stFirst = (data.student_first_name || data.payer_first_name).toUpperCase();
    const stMid = (data.student_middle_name || data.payer_middle_name).toUpperCase();
    drawCells(page2, stLast, 70.86, 107.30);
    drawCells(page2, stFirst, 70.86, 132.80);
    drawCells(page2, stMid, 70.86, 158.30);
    const stBirth = data.student_birth_date || data.payer_birth_date;
    if (stBirth) drawDate(page2, stBirth, 368.50, 183.80);

    drawCells(page2, data.doc_code || '21', 113.38, 232.00);
    const stSn = (data.student_doc_series && data.student_doc_num) ? `${data.student_doc_series} ${data.student_doc_num}` : sn;
    drawCells(page2, stSn, 297.63, 232.00);
    const stIssue = data.student_doc_issue_date || data.doc_issue_date;
    if (stIssue) drawDate(page2, stIssue, 113.38, 257.50);

    if (data.doc_date) {
      page2.drawText(data.doc_date, {
        x: 378.00,
        y: 16.13,
        size: 11,
        font: helveticaFont
      });
    }
  }

  const pdfBytes = await pdfDoc.save();
  return new Blob([pdfBytes], { type: "application/pdf" });
}

// Загрузка файла через браузер
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Настройка интерактивного холста подписи
function setupSignaturePad() {
  const modal = document.getElementById("drawSigModal");
  const canvas = document.getElementById("sigCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let isDrawing = false;
  ctx.strokeStyle = "#1e3a8a"; // Синие чернила
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  document.getElementById("btnDrawSig").addEventListener("click", () => {
    modal.classList.remove("hidden");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  document.getElementById("btnCloseSigModal").addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  document.getElementById("btnClearSig").addEventListener("click", () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  function startPos(e) {
    isDrawing = true;
    draw(e);
  }
  function endPos() {
    isDrawing = false;
    ctx.beginPath();
  }
  function draw(e) {
    if (!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX)) - rect.left;
    const y = (e.clientY || (e.touches && e.touches[0].clientY)) - rect.top;
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  canvas.addEventListener("mousedown", startPos);
  canvas.addEventListener("mouseup", endPos);
  canvas.addEventListener("mousemove", draw);

  canvas.addEventListener("touchstart", (e) => { e.preventDefault(); startPos(e); });
  canvas.addEventListener("touchend", endPos);
  canvas.addEventListener("touchmove", (e) => { e.preventDefault(); draw(e); });

  document.getElementById("btnSaveSig").addEventListener("click", () => {
    const dataUrl = canvas.toDataURL("image/png");
    document.getElementById("sigPreviewImg").src = dataUrl;
    currentConfig.signature_data_url = dataUrl;
    modal.classList.add("hidden");
  });

  // Загрузка своего файла подписи
  document.getElementById("sigFileInput").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (re) => {
        document.getElementById("sigPreviewImg").src = re.target.result;
        currentConfig.signature_data_url = re.target.result;
      };
      reader.readAsDataURL(file);
    }
  });
}

// Настройка пакетной загрузки
function setupBatchUpload() {
  const dropZone = document.getElementById("batchDropZone");
  const fileInput = document.getElementById("batchFileInput");
  if (!dropZone) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleBatchFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
      handleBatchFile(e.target.files[0]);
    }
  });
}

let loadedBatchRecords = [];

async function handleBatchFile(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith(".csv")) {
    const text = await file.text();
    parseBatchCsv(text);
  } else if (name.endsWith(".xlsx")) {
    // Отправляем на сервер для чтения или уведомляем
    alert(`Файл '${file.name}' загружен. Нажмите «Запустить генерацию», сервер обработает таблицу.`);
    showBatchExcelPlaceholder(file.name);
  }
}

function parseBatchCsv(csvText) {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return;

  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  loadedBatchRecords = [];

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",").map((c) => c.trim());
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = cols[idx] || "";
    });
    loadedBatchRecords.push(row);
  }

  renderBatchTable(loadedBatchRecords);
}

function showBatchExcelPlaceholder(filename) {
  const card = document.getElementById("batchPreviewCard");
  card.style.display = "block";
  document.getElementById("batchCountBadge").textContent = "Excel файл";
  const tbody = document.getElementById("batchTableBody");
  tbody.innerHTML = `<tr><td colspan="8">Готов к обработке на сервере: <strong>${filename}</strong></td></tr>`;

  document.getElementById("btnStartBatch").onclick = async () => {
    alert("Для обработки Excel файлов запустите в терминале команду:\npython cli.py --batch " + filename);
  };
}

function renderBatchTable(records) {
  const card = document.getElementById("batchPreviewCard");
  card.style.display = "block";
  document.getElementById("batchCountBadge").textContent = records.length;

  const tbody = document.getElementById("batchTableBody");
  tbody.innerHTML = "";

  records.forEach((r, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td>${r.number || "-"}</td>
      <td><strong>${r.last_name || r.fio || "-"}</strong> ${r.first_name || ""}</td>
      <td>${r.birth_date || "-"}</td>
      <td>${r.passport || "-"}</td>
      <td>${r.amount || "0"} руб.</td>
      <td>${r.year || "2025"}</td>
      <td><span class="badge" style="background:#e0f2fe;color:#0369a1;">Готов</span></td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById("btnStartBatch").onclick = runBatchProcess;
}

async function runBatchProcess() {
  const btn = document.getElementById("btnStartBatch");
  btn.disabled = true;
  btn.innerHTML = "⏳ Генерация...";

  try {
    const resp = await fetch("/api/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: loadedBatchRecords })
    });

    if (resp.ok) {
      const result = await resp.json();
      const resCard = document.getElementById("batchResultsCard");
      resCard.style.display = "block";
      const list = document.getElementById("batchResultsList");
      list.innerHTML = `
        <div class="alert-info mb-2">✓ Успешно сгенерировано справок: ${result.count}. Все файлы сохранены в папку <code>output/</code>.</div>
        <ul>
          ${result.files.map((f) => `<li><a href="/output/${encodeURIComponent(f.filename)}" target="_blank">📄 ${f.filename}</a></li>`).join("")}
        </ul>
      `;
      alert(`✓ Успешно сгенерировано ${result.count} справок в папку output/!`);
    } else {
      alert("Ошибка при пакетной генерации на сервере");
    }
  } catch (e) {
    alert("Ошибка соединения с сервером. Запустите 'python app.py' для пакетной генерации.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🚀 Запустить генерацию всех справок";
  }
}
