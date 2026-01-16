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

const searchInput = document.getElementById('searchInput');
const items = document.querySelectorAll('.link-list a, .link-list li');

searchInput.addEventListener('input', () => {
  const keyword = searchInput.value.toLowerCase().trim();
  let firstMatch = null;

  items.forEach(el => {
    const text = el.textContent.toLowerCase();

    if (text.includes(keyword)) {
      el.style.display = '';
      if (!firstMatch && keyword !== '') {
        firstMatch = el;
      }
    } else {
      el.style.display = 'none';
    }
  });

  // ⭐ 自动滚动到第一个结果
  if (firstMatch) {
    firstMatch.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
});

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

// document.getElementById("qaSubmit").addEventListener("click", function () {
  // const password = "Duke2030";   // ← 改成你的
 // const input = document.getElementById("qaPassword").value;
//  const qa = document.querySelector(".qa-content");

 // if (input === password) {
 //   qa.style.display = "block";
//  } else {
//    alert("密码错误");
//  }
// });



// ===== Q&A 密码保护 =====
 const qaPassword = "Duke2030";  // 设置你的密码
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

// 保持折叠互斥
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

// 24届
// function loadCSV24() {
//  const correctPassword = "Duke2024";   // ← 改成你的密码
//  const input = document.getElementById("csvPassword").value;
//  const error = document.getElementById("csv-error");

//  if (input !== correctPassword) {
//    error.textContent = "密码错误";
//  return;
//  }

//  error.textContent = "";

//  fetch("24届毕业去向.csv")
//    .then(res => res.text())
//    .then(text => {
//      const rows = text.trim().split("\n");
   //   const table = document.getElementById("csvTable");
 //     table.innerHTML = "";

 //     rows.forEach((row, i) => {
  //      const tr = document.createElement("tr");
 //       row.split(",").forEach(cell => {
//          const el = i === 0 ? "th" : "td";
 //         const td = document.createElement(el);
   //       td.textContent = cell;
 //         tr.appendChild(td);
//        });
//        table.appendChild(tr);
//      });

//      document.getElementById("csv-password-box").style.display = "none";
//    });
// }

// 25届
// function loadCSV25() {
//  const correctPassword = "Duke2025";   // ← 改成你的密码
//  const input = document.getElementById("csvPassword").value;
//  const error = document.getElementById("csv-error");
//  if (input !== correctPassword) {
//    error.textContent = "密码错误";
//    return;
//  }

//  error.textContent = "";
//
//  fetch("25届毕业去向.csv")
//    .then(res => res.text())
//    .then(text => {
//      const rows = text.trim().split("\n");
   //   const table = document.getElementById("csvTable");
 //     table.innerHTML = "";

  //    rows.forEach((row, i) => {
//        const tr = document.createElement("tr");
   //     row.split(",").forEach(cell => {
//          const el = i === 0 ? "th" : "td";
//          const td = document.createElement(el);
  //        td.textContent = cell;
 //         tr.appendChild(td);
  //      });
 //       table.appendChild(tr);
  //    });

 //     document.getElementById("csv-password-box").style.display = "none";
//    });
// }



/* ========= CSV 工具函数 ========= */
function renderCSV(csvText, tableId) {
  const rows = csvText.trim().split("\n");
  const table = document.getElementById(tableId);
  table.innerHTML = "";

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

/* ========= 24届 ========= */
function loadCSV24() {
  const pwd = document.getElementById("csvPwd24").value;
  const err = document.getElementById("csvErr24");

  if (pwd !== "Duke2024") {
    err.textContent = "❌ 密码错误";
    return;
  }

  fetch("24届毕业去向.csv")
    .then(res => res.text())
    .then(text => renderCSV(text, "csvTable24"));

  err.textContent = "";
  document.getElementById("csv-box-24").style.display = "none";
}

/* ========= 25届 ========= */
function loadCSV25() {
  const pwd = document.getElementById("csvPwd25").value;
  const err = document.getElementById("csvErr25");

  if (pwd !== "Duke2025") {
    err.textContent = "❌ 密码错误";
    return;
  }

  fetch("25届毕业去向.csv")
    .then(res => res.text())
    .then(text => renderCSV(text, "csvTable25"));

  err.textContent = "";
  document.getElementById("csv-box-25").style.display = "none";
}
