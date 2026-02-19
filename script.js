// =======================================
// CSV 加载函数
// =======================================
// 注意：图片放大、视频放大、PPT、搜索、Q&A 的事件绑定
// 已移至 index.html 的 showContent() 函数中处理，
// 因为这些元素是登录后从 <template> 克隆插入的，
// DOMContentLoaded 时它们还不存在。

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

// 30届
function loadCSV30() {
  const pwd = document.getElementById("csvPwd30").value;
  const err = document.getElementById("csvErr30");

  if (pwd !== "2030Duke") {
    err.textContent = "❌ 密码错误";
    return;
  }

  fetch("class30.csv")
    .then(res => res.text())
    .then(text => renderCSV(text, "csvTable30"))
    .catch(() => err.textContent = "❌ CSV 文件加载失败");

  err.textContent = "";
  document.getElementById("csv-password-box-30").style.display = "none";
  document.getElementById("csv-container-30").style.display = "block";
}

// 24届
function loadCSV24() {
  const pwd = document.getElementById("csvPwd24").value;
  const err = document.getElementById("csvErr24");

  if (pwd !== "Duke2024") {
    err.textContent = "❌ 密码错误";
    return;
  }

  fetch("24graduate.csv")
    .then(res => res.text())
    .then(text => renderCSV(text, "csvTable24"))
    .catch(() => err.textContent = "❌ CSV 文件加载失败");

  err.textContent = "";
  document.getElementById("csv-password-box-24").style.display = "none";
  document.getElementById("csv-container-24").style.display = "block";
}

// 25届
function loadCSV25() {
  const pwd = document.getElementById("csvPwd25").value;
  const err = document.getElementById("csvErr25");

  if (pwd !== "Duke2025") {
    err.textContent = "❌ 密码错误";
    return;
  }

  fetch("25graduate.csv")
    .then(res => res.text())
    .then(text => renderCSV(text, "csvTable25"))
    .catch(() => err.textContent = "❌ CSV 文件加载失败");

  err.textContent = "";
  document.getElementById("csv-password-box-25").style.display = "none";
  document.getElementById("csv-container-25").style.display = "block";
}

// 关闭表格
function closeCSV(year) {
  const container = document.getElementById("csv-container-" + year);
  if (container) container.style.display = "none";
  const pwdBox = document.getElementById("csv-password-box-" + year);
  if (pwdBox) pwdBox.style.display = "block";
}
