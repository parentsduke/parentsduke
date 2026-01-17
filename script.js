// =======================================
// DOM 操作：图片/视频/搜索/PPT/Q&A
// =======================================
document.addEventListener("DOMContentLoaded", () => {

  // ========== 图片单击放大 ==========
  document.querySelectorAll('.thumb').forEach(img => {
    img.addEventListener('click', () => {
      const overlay = document.getElementById('overlay');
      const overlayImg = document.getElementById('overlay-img');
      overlayImg.src = img.src;
      overlay.style.display = 'flex';
    });
  });

  document.getElementById('overlay').addEventListener('click', () => {
    document.getElementById('overlay').style.display = 'none';
  });

  // ========== 视频单击放大 ==========
  document.querySelectorAll('.video-wrapper').forEach(wrapper => {
    const video = wrapper.querySelector('.video-box');
    const clickLayer = wrapper.querySelector('.video-click-layer');
    const overlay = document.getElementById('video-overlay');
    const overlayVideo = document.getElementById('overlay-video');

    clickLayer.addEventListener('click', () => {
      overlayVideo.src = video.currentSrc || video.src;
      overlay.style.display = 'flex';
      overlayVideo.play();
    });
  });

  document.getElementById('video-overlay').addEventListener('click', () => {
    const overlayVideo = document.getElementById('overlay-video');
    overlayVideo.pause();
    overlayVideo.src = '';
    document.getElementById('video-overlay').style.display = 'none';
  });

  // ========== 搜索功能 ==========
  const searchInput = document.getElementById('searchInput');
  const items = document.querySelectorAll('.link-list a, .link-list li');

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const keyword = searchInput.value.toLowerCase().trim();
      let firstMatch = null;

      items.forEach(el => {
        const text = el.textContent.toLowerCase();
        if (text.includes(keyword)) {
          el.style.display = '';
          if (!firstMatch && keyword !== '') firstMatch = el;
        } else {
          el.style.display = 'none';
        }
      });

      if (firstMatch) {
        firstMatch.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }
    });
  }

  // ===== PPT 折叠控制 =====
  const pptToggle = document.getElementById("pptToggle");
  const pptContent = document.getElementById("pptContent");

  if (pptToggle && pptContent) {
    pptToggle.addEventListener("click", () => {
      const isOpen = pptContent.style.display === "block";
      pptContent.style.display = isOpen ? "none" : "block";
      pptToggle.textContent = isOpen ? "展开" : "收起";
    });
  }

  // ===== Q&A 密码保护 =====
  const qaPassword = "Duke2030";  
  const qaContent = document.querySelector(".qa-content");
  const qaInput = document.getElementById("qaPassword");
  const qaSubmit = document.getElementById("qaSubmit");

  qaSubmit.addEventListener("click", () => {
    if (qaInput.value === qaPassword) {
      qaContent.style.display = "block";
      qaInput.style.display = "none";
      qaSubmit.style.display = "none";
    } else {
      alert("密码错误，请重试！");
    } 
  });

  // 保持 Q&A 折叠互斥
  const qaDetails = document.querySelectorAll('.qa-content details');
  qaDetails.forEach(detail => {
    detail.addEventListener('toggle', () => {
      if (detail.open) {
        qaDetails.forEach(other => {
          if (other !== detail) other.removeAttribute('open');
        });
      }
    });
  });

}); // ← DOMContentLoaded 结束

// =======================================
// CSV 加载函数（全局，可直接调用 loadCSV24()/loadCSV25()）
// =======================================

// 渲染 CSV 表格
//function renderCSV(csvText, tableId) {
//  const rows = csvText.trim().split("\n");
//  const table = document.getElementById(tableId);
//  table.innerHTML = "";
//  table.style.display = ""; // 显示表格

//  rows.forEach((row, i) => {
//    const tr = document.createElement("tr");
//    row.split(",").forEach(cell => {
 //     const el = document.createElement(i === 0 ? "th" : "td");
//      el.textContent = cell;
//      tr.appendChild(el);
 //   });
//    table.appendChild(tr);
//  });
// }

// 24届 CSV 加载
// function loadCSV24() {
//  const pwd = document.getElementById("csvPwd24").value;
//  const err = document.getElementById("csvErr24");

//  if (pwd !== "Duke2024") {
//    err.textContent = "❌ 密码错误";
//    return;
//  }

//  fetch("24graduate.csv")
//   .then(res => res.text())
 //   .then(text => renderCSV(text, "csvTable24"))
//    .catch(() => err.textContent = "❌ CSV 文件加载失败");

//  err.textContent = "";
//  document.getElementById("csv-password-box-24").style.display = "none";
// }

// 25届 CSV 加载
// function loadCSV25() {
//  const pwd = document.getElementById("csvPwd25").value;
//  const err = document.getElementById("csvErr25");

//  if (pwd !== "Duke2025") {
 //   err.textContent = "❌ 密码错误";
//    return;
//  }

//  fetch("25graduate.csv")
//    .then(res => res.text())
//    .then(text => renderCSV(text, "csvTable25"))
//    .catch(() => err.textContent = "❌ CSV 文件加载失败");

//  err.textContent = "";
//  document.getElementById("csv-password-box-25").style.display = "none";
// }

// =======================================
// CSV 加载函数（高级表格风格）
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
}

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
}
