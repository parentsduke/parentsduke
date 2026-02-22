// =======================================
// Supabase client（与 index.html 共用同一个实例）
// script.js 里不重复初始化，直接用 window._supabaseClient
// 该变量由 index.html 在登录成功后挂载到 window 上
// =======================================

function getClient() {
  return window._supabaseClient;
}

// =======================================
// CSV 渲染（不变）
// =======================================
function renderCSV(csvText, tableId) {
  const rows = csvText.trim().split("\n");
  const table = document.getElementById(tableId);
  table.innerHTML = "";
  table.style.display = "";

  rows.forEach((row, i) => {
    const tr = document.createElement("tr");
    row.split(",").forEach(cell => {
      const el = document.createElement(i === 0 ? "th" : "td");
      el.textContent = cell;
      tr.appendChild(el);
    });
    table.appendChild(tr);
  });
}

// =======================================
// 通用：向 Supabase 验证 CSV 密码
// 密码不再写在前端！
// =======================================
async function verifyCSVPassword(csvName, inputPassword) {
  const client = getClient();
  if (!client) return false;

  const { data, error } = await client
    .from("csv_access")
    .select("password")
    .eq("name", csvName)
    .single();

  if (error || !data) return false;
  return data.password === inputPassword;
}

// =======================================
// 通用：加载 CSV 文件
// =======================================
async function loadCSV(csvName, csvFile, pwdInputId, errId, pwdBoxId, containerId, tableId) {
  const pwd = document.getElementById(pwdInputId).value;
  const err = document.getElementById(errId);

  err.textContent = "验证中...";

  const ok = await verifyCSVPassword(csvName, pwd);

  if (!ok) {
    err.textContent = "密码错误";
    return;
  }

  fetch(csvFile)
    .then(res => res.text())
    .then(text => renderCSV(text, tableId))
    .catch(() => { err.textContent = "CSV 文件加载失败"; });

  err.textContent = "";
  document.getElementById(pwdBoxId).style.display = "none";
  document.getElementById(containerId).style.display = "block";
}

// =======================================
// 30届
// =======================================
function loadCSV30() {
  loadCSV("class30", "class30.csv", "csvPwd30", "csvErr30",
          "csv-password-box-30", "csv-container-30", "csvTable30");
}

// =======================================
// 24届
// =======================================
function loadCSV24() {
  loadCSV("class24", "24graduate.csv", "csvPwd24", "csvErr24",
          "csv-password-box-24", "csv-container-24", "csvTable24");
}

// =======================================
// 25届
// =======================================
function loadCSV25() {
  loadCSV("class25", "25graduate.csv", "csvPwd25", "csvErr25",
          "csv-password-box-25", "csv-container-25", "csvTable25");
}

// =======================================
// 关闭表格
// =======================================
function closeCSV(year) {
  const container = document.getElementById("csv-container-" + year);
  if (container) container.style.display = "none";
  const pwdBox = document.getElementById("csv-password-box-" + year);
  if (pwdBox) pwdBox.style.display = "block";
}
