
// ===== 管理员面板逻辑 =====
const ADMIN_PASSWORD = "Jyswswhj098)(*"; // ← 可在此修改管理员密码

var adminPendingFiles = [];

function toggleAdminPanel() {
  var panel = document.getElementById("admin-panel");
  panel.style.display = panel.style.display === "none" ? "block" : "none";
}

function verifyAdmin() {
  var pwd = document.getElementById("adminPwdInput").value;
  var err = document.getElementById("adminLoginErr");
  if (pwd === ADMIN_PASSWORD) {
    document.getElementById("admin-login-box").style.display = "none";
    document.getElementById("admin-upload-area").style.display = "block";
    loadAdminFileList();
    loadApprovedPhotoManager();
    loadApprovedVideoManager();
    loadApprovedFileManager();
    loadApprovedYuanfenManager();
    loadApprovedJingcaiManager();
    loadAlbumPhotoManager();
    loadVideoGallery();
    loadApprovedAdminVideoManager();
    loadPendingUploads();
    loadPendingVideos();
    loadPendingPpts();
    loadPendingYuanfen();
    loadPendingJingcai();
    loadXdxEntries();
    // 默认显示新动向tab
    switchAdminTab('xindongxiang', document.querySelector('.admin-tab-btn'));
    // 读取已保存的API key
    var savedKey = localStorage.getItem('xdx_api_key');
    if (savedKey) { var keyInput = document.getElementById('xdx-api-key'); if (keyInput) keyInput.value = savedKey; }
    err.textContent = "❌ 密码错误，请重试";
  }
}

document.addEventListener("keydown", function(e) {
  var input = document.getElementById("adminPwdInput");
  if (input && document.activeElement === input && e.key === "Enter") verifyAdmin();
});

function adminLogout() {
  document.getElementById("admin-upload-area").style.display = "none";
  document.getElementById("admin-login-box").style.display = "block";
  document.getElementById("adminPwdInput").value = "";
  document.getElementById("adminLoginErr").textContent = "";
  adminPendingFiles = [];
  document.getElementById("adminUploadList").innerHTML = "";
  document.getElementById("adminUploadBtn").style.display = "none";
}

function adminDragOver(e) {
  e.preventDefault();
  document.getElementById("adminDropZone").style.background = "#d8e8fc";
}
function adminDragLeave(e) {
  document.getElementById("adminDropZone").style.background = "#eef3fa";
}
function adminDrop(e) {
  e.preventDefault();
  adminDragLeave(e);
  handleAdminFiles(e.dataTransfer.files);
}

function handleAdminFiles(files) {
  adminPendingFiles = Array.from(files);
  var list = document.getElementById("adminUploadList");
  list.innerHTML = "";

  if (!adminPendingFiles.length) return;

  adminPendingFiles.forEach(function(file) {
    var item = document.createElement("div");
    item.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 12px;border:1px solid #e0e0e0;border-radius:6px;margin-bottom:6px;background:#fff;";

    var icon = file.type.startsWith("image/") ? "🖼" :
               file.type.startsWith("video/") ? "🎬" :
               file.type === "application/pdf" ? "📄" : "📦";

    var size = file.size > 1024*1024 ? (file.size/1024/1024).toFixed(1)+"MB" : (file.size/1024).toFixed(0)+"KB";

    item.innerHTML = '<span style="font-size:20px;">'+icon+'</span>' +
      '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px;">'+file.name+'</span>' +
      '<span style="color:#888;font-size:12px;white-space:nowrap;">'+size+'</span>' +
      '<span class="upload-status-'+sanitizeId(file.name)+'" style="font-size:12px;color:#888;">待上传</span>';
    list.appendChild(item);
  });

  document.getElementById("adminUploadBtn").style.display = "inline-block";
}

function sanitizeId(name) {
  return name.replace(/[^a-zA-Z0-9]/g, "_");
}

async function startAdminUpload() {
  if (!adminPendingFiles.length) return;

  var supabase = window._supabaseClient;
  if (!supabase) { alert("Supabase 未初始化，请确保已登录页面"); return; }

  var folder = document.getElementById("adminFolderSelect").value;
  var btn = document.getElementById("adminUploadBtn");
  btn.disabled = true;
  btn.textContent = "上传中...";

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  for (var i = 0; i < adminPendingFiles.length; i++) {
    var file = adminPendingFiles[i];
    var statusEl = document.querySelector(".upload-status-" + sanitizeId(file.name));
    if (statusEl) { statusEl.textContent = "上传中..."; statusEl.style.color = "#003366"; }

    var filePath = folder + "/" + Date.now() + "_" + file.name;
    var result = await supabase.storage.from("uploads").upload(filePath, file, { upsert: true });

    if (result.error) {
      if (statusEl) { statusEl.textContent = "失败"; statusEl.style.color = "crimson"; }
      continue;
    }

    // 非图片分类：直接完成
    if (!(folder === "images" && file.type.startsWith("image/"))) {
      if (statusEl) { statusEl.textContent = "成功"; statusEl.style.color = "green"; }
      continue;
    }

    // 图片分类：先写一条 pending 记录，再调 Edge Function 转存到 GitHub
    if (statusEl) { statusEl.textContent = "转存 GitHub 中..."; statusEl.style.color = "#c07000"; }

    var displayName = file.name.replace(/\.[^.]+$/, "");

    // 插入临时记录（pending），获取 id 供 Edge Function 使用
    var dbInsert = await supabase.from("pending_uploads").insert({
      file_path: filePath,
      file_name: file.name,
      title: displayName,
      uploaded_by: "admin",
      status: "pending",
      file_type: "image"
    }).select().single();

    if (dbInsert.error) {
      if (statusEl) { statusEl.textContent = "数据库写入失败"; statusEl.style.color = "crimson"; }
      continue;
    }

    var pendingId = dbInsert.data.id;

    // 调用 Edge Function 转存到 GitHub（会自动更新记录状态为 approved，file_path 改为 github: URL）
    try {
      if (statusEl) { statusEl.textContent = "转存 GitHub 中..."; statusEl.style.color = "#c07000"; }
      var ghUrl = await uploadToGitHubViaEdge(pendingId, "images");
      if (statusEl) { statusEl.textContent = "成功 ✓ GitHub"; statusEl.style.color = "green"; }
      // 加入风景线（使用 GitHub URL）
      addAdminAlbumPhoto(ghUrl, displayName);
    } catch (e) {
      // 转存失败：删除 pending 记录，提示用户具体错误
      await supabase.from("pending_uploads").delete().eq("id", pendingId);
      var errMsg = e.message || "未知错误";
      if (statusEl) {
        statusEl.textContent = "GitHub转存失败";
        statusEl.style.color = "crimson";
        statusEl.title = errMsg; // 鼠标悬停可看详细错误
      }
      console.error("[GitHub转存失败] 文件:", file.name, "| 错误:", errMsg);
      alert("图片「" + file.name + "」转存 GitHub 失败：\n" + errMsg + "\n\n请检查：\n1. Supabase Edge Function「github-upload」是否已部署\n2. Edge Function 中的 GitHub Token 是否有效\n3. GitHub 仓库名/路径配置是否正确");
    }
  }

  btn.textContent = "上传完成";
  btn.disabled = false;
  adminPendingFiles = [];
  loadAdminFileList();
}

async function loadAdminFileList() {
  var supabase = window._supabaseClient;
  if (!supabase) return;

  var content = document.getElementById("adminFileListContent");
  content.innerHTML = '<span style="color:#888;">加载中...</span>';

  var folders = ["images", "videos", "documents", "misc"];
  var allFiles = [];

  for (var i = 0; i < folders.length; i++) {
    var result = await supabase.storage.from("uploads").list(folders[i], { limit: 100, sortBy: { column: "created_at", order: "desc" } });
    if (result.data && result.data.length) {
      result.data.forEach(function(f) {
        allFiles.push({ folder: folders[i], file: f });
      });
    }
  }

  if (!allFiles.length) {
    content.innerHTML = '<span style="color:#aaa;">暂无上传文件</span>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
  html += '<tr style="background:#003366;color:#fff;"><th style="padding:8px;text-align:left;">文件名</th><th style="padding:8px;">分类</th><th style="padding:8px;">大小</th><th style="padding:8px;">操作</th></tr>';

  allFiles.forEach(function(item, idx) {
    var f = item.file;
    var size = f.metadata && f.metadata.size ? (f.metadata.size > 1024*1024 ? (f.metadata.size/1024/1024).toFixed(1)+"MB" : (f.metadata.size/1024).toFixed(0)+"KB") : "-";
    var filePath = item.folder + "/" + f.name;
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + filePath;
    var bg = idx % 2 === 0 ? "#fff" : "#f4f4f4";

    // 文件名（去掉时间戳前缀）
    var displayName = f.name.replace(/^\d+_/, "");

    html += '<tr style="background:'+bg+';">' +
      '<td style="padding:7px 8px;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+f.name+'">'+displayName+'</td>' +
      '<td style="padding:7px 8px;text-align:center;color:#555;">'+item.folder+'</td>' +
      '<td style="padding:7px 8px;text-align:center;color:#777;">'+size+'</td>' +
      '<td style="padding:7px 8px;text-align:center;">' +
        '<a href="'+pubUrl+'" target="_blank" style="color:#003366;text-decoration:none;margin-right:8px;">🔗 链接</a>' +
        '<button onclick="copyAdminUrl(\''+pubUrl+'\')" style="padding:3px 8px;font-size:12px;cursor:pointer;border:1px solid #ccc;border-radius:4px;background:#fff;">复制链接</button>' +
        ' <button onclick="deleteAdminFile(\''+filePath+'\',\''+item.folder+'\')" style="padding:3px 8px;font-size:12px;cursor:pointer;border:1px solid #faa;border-radius:4px;background:#fff8f8;color:#c00;">' + (item.folder === 'images' ? '🗑 删除（含相册）' : '删除') + '</button>' +
      '</td></tr>';
  });
  html += '</table>';
  content.innerHTML = html;
}

function copyAdminUrl(url) {
  navigator.clipboard.writeText(url).then(function() {
    alert("链接已复制到剪贴板！\n\n" + url);
  });
}

async function deleteAdminFile(filePath, folder) {
  var isImage = folder === "images";
  var msg = isImage
    ? "确认删除此图片？\n将同时从风景线中移除。\n\n" + filePath
    : "确认删除此文件？\n" + filePath;
  if (!confirm(msg)) return;

  var supabase = window._supabaseClient;
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  // 1. 删除 Supabase Storage 文件
  var result = await supabase.storage.from("uploads").remove([filePath]);
  if (result.error) {
    alert("删除失败：" + result.error.message);
    return;
  }

  // 2. 如果是图片，同步删除 pending_uploads 表记录
  //    数据库里 file_path 可能是原始路径，也可能是 github:URL（Edge Function 转存后会更新）
  if (isImage) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + filePath;

    // 先尝试匹配原始路径，再尝试匹配 github: 前缀
    var delResult = await supabase.from("pending_uploads").delete().eq("file_path", filePath);
    if (!delResult.error) {
      // 也尝试删除可能存在的 github: 格式记录（Edge Function 转存后 file_path 被改写）
      await supabase.from("pending_uploads").delete().like("file_path", "github:%").eq("file_name", filePath.split("/").pop());
    }

    // 3. 从风景线轮播中移除
    removeAdminAlbumPhoto(pubUrl);
    // 同时尝试移除 GitHub raw URL（如果 Edge Function 成功转存过）
    var track = document.getElementById("adminSlideshowTrack");
    if (track) {
      Array.from(track.querySelectorAll(".slide img")).forEach(function(img) {
        var fileName = filePath.split("/").pop();
        if (img.src && img.src.includes(fileName)) {
          removeAdminAlbumPhoto(img.src);
        }
      });
    }
  }

  alert("已删除");
  loadAdminFileList();
}

// ===== 风景线管理（管理员可选择性删除）=====
// ===== Tab 切换 =====
function switchAdminTab(tab, btn) {
  document.querySelectorAll('.admin-tab-panel').forEach(function(p) { p.style.display = 'none'; });
  document.querySelectorAll('.admin-tab-btn').forEach(function(b) { b.classList.remove('admin-tab-active'); });
  var panel = document.getElementById('adminTab-' + tab);
  if (panel) panel.style.display = 'block';
  if (btn) btn.classList.add('admin-tab-active');
  if (tab === 'xindongxiang') loadXdxEntries();
}

// ===== Resend 邮件通知（通过Supabase Edge Function） =====
async function sendResendNotification(type, title, submittedBy) {
  try {
    await fetch('https://ritglkwqpwlcjwemhfqd.supabase.co/functions/v1/send-notification', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpdGdsa3dxcHdsY2p3ZW1oZnFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3MzEyMTQsImV4cCI6MjA4NzMwNzIxNH0.TqjETAEGcWTd2CbvkMnmfm6bKHLtZHjXbsy3dtPuEB8'
      },
      body: JSON.stringify({ type, title, submittedBy })
    });
  } catch(e) {
    console.warn('[通知发送失败]', e.message);
  }
}

// ===== 新动向 AI生成与管理 =====

async function generateXdxEntry() {
  var title = document.getElementById('xdx-title').value.trim();
  var summary = document.getElementById('xdx-summary').value.trim();
  var url = document.getElementById('xdx-url').value.trim();
  var date = document.getElementById('xdx-date').value.trim();
  var apiKey = (document.getElementById('xdx-api-key') && document.getElementById('xdx-api-key').value.trim()) || localStorage.getItem('xdx_api_key') || '';
  if (!title || !summary) {
    alert('请填写文章标题和摘要');
    return;
  }
  if (!apiKey) {
    alert('请填写 Anthropic API Key');
    return;
  }
  document.getElementById('xdx-loading').style.display = 'inline';
  document.getElementById('xdx-gen-btn').disabled = true;
  document.getElementById('xdx-preview-box').style.display = 'none';

  var prompt = `你是一个帮助管理杜克大学中文家长群网站的助手。请根据以下文章信息，生成一段中文网页内容，供插入"新动向"手风琴区块中作为一个子手风琴条目。

文章标题：${title}
${date ? '发布日期：' + date : ''}
${url ? '原文链接：' + url : ''}
文章内容/摘要：
${summary}

请生成一个子手风琴条目的HTML，格式严格参照以下模板，只返回HTML代码，不要任何解释或markdown代码块标记：

<div class="sub-accordion">
  <button class="sub-accordion-btn" onclick="toggleSubAccordion(this)">
    <span>[简短中文标题]<span class="tag tag-key">[日期如2026.3.6]</span></span>
    <span class="sub-accordion-arrow">&#9658;</span>
  </button>
  <div class="sub-accordion-body">
    <div class="cal-highlight">
      <strong>[核心要点标题]</strong><br>
      [2-3句话概括文章最重要内容，面向中国家长，语言简洁]
    </div>
    <div class="cal-item">
      <div class="cal-date">[要点标签]</div>
      <div><div class="cal-desc">[具体内容]</div></div>
    </div>
    [如有更多要点，继续添加cal-item]
    ${url ? '<a href="' + url + '" target="_blank">原文链接（Duke Chronicle）</a>' : ''}
  </div>
</div>

注意：
- tag颜色选择：重要用tag-key(紫)，春季/积极用tag-spring(绿)，秋季/警示用tag-fall(橙)，假日用tag-holiday(蓝)，期末/截止用tag-exam(红)，家长相关用tag-family(金)
- 语言要简洁、专业，适合中国家长阅读
- 只输出HTML，不要任何其他文字`;

  try {
    var res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }]
      })
    });
    var data = await res.json();
    if (data.error) throw new Error(data.error.message || 'API错误');
    var html = (data.content || []).map(function(b) { return b.text || ''; }).join('').trim();
    // 去除可能的markdown代码块
    html = html.replace(/^```html\n?/i, '').replace(/\n?```$/i, '').trim();
    document.getElementById('xdx-preview').value = html;
    document.getElementById('xdx-preview-box').style.display = 'block';
    document.getElementById('xdx-publish-msg').textContent = '';
  } catch(e) {
    alert('AI生成失败：' + e.message);
  }
  document.getElementById('xdx-loading').style.display = 'none';
  document.getElementById('xdx-gen-btn').disabled = false;
}

async function publishXdxEntry() {
  var html = document.getElementById('xdx-preview').value.trim();
  if (!html) return;
  var supabase = window._supabaseClient;
  if (!supabase) { alert('数据库未连接'); return; }
  var title = document.getElementById('xdx-title').value.trim();
  var date = document.getElementById('xdx-date').value.trim() || new Date().toLocaleDateString('zh-CN');
  var msg = document.getElementById('xdx-publish-msg');

  try {
    var res = await supabase.from('xdx_entries').insert({ title: title, date: date, html: html });
    if (res.error) throw new Error(res.error.message);
    msg.style.color = '#0a7c3e';
    msg.textContent = '✅ 发布成功！已显示在新动向中。';
    loadXdxEntries();
    document.getElementById('xdx-title').value = '';
    document.getElementById('xdx-url').value = '';
    document.getElementById('xdx-summary').value = '';
    document.getElementById('xdx-date').value = '';
    setTimeout(function() { document.getElementById('xdx-preview-box').style.display = 'none'; }, 1500);
  } catch(e) {
    msg.style.color = 'crimson';
    msg.textContent = '发布失败：' + e.message;
  }
}

async function loadXdxEntries() {
  var list = document.getElementById('xdx-entries-list');
  if (!list) return;
  var supabase = window._supabaseClient;
  if (!supabase) { list.innerHTML = '<span style="color:crimson;">数据库未连接</span>'; return; }
  try {
    var res = await supabase.from('xdx_entries').select('*').order('created_at', { ascending: false });
    if (res.error) throw new Error(res.error.message);
    var entries = res.data || [];
    renderXdxDynamic(entries);
    if (entries.length === 0) {
      list.innerHTML = '<span style="color:#aaa;">暂无动态发布的条目</span>';
      return;
    }
    list.innerHTML = entries.map(function(e) {
      return '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #eee;">' +
        '<div><span style="font-weight:600;color:#003366;">' + (e.title || '无标题') + '</span><span style="color:#aaa;font-size:11px;margin-left:8px;">' + (e.date || '') + '</span></div>' +
        '<button data-xdx-id="' + e.id + '" onclick="deleteXdxEntry(this.getAttribute(\'data-xdx-id\'))" style="padding:4px 10px;background:#fdd;border:1px solid #e99;border-radius:4px;font-size:12px;cursor:pointer;color:#900;">删除</button>' +
        '</div>';
    }).join('');
  } catch(e) {
    list.innerHTML = '<span style="color:crimson;">加载失败：' + e.message + '</span>';
  }
}

async function deleteXdxEntry(id) {
  if (!confirm('确认删除此条目？')) return;
  var supabase = window._supabaseClient;
  if (!supabase) return;
  try {
    var res = await supabase.from('xdx_entries').delete().eq('id', id);
    if (res.error) throw new Error(res.error.message);
    loadXdxEntries();
  } catch(e) { alert('删除失败：' + e.message); }
}

function renderXdxDynamic(entries) {
  var container = document.getElementById('xdx-dynamic-entries');
  if (!container) return;
  if (!entries || entries.length === 0) { container.innerHTML = ''; return; }
  container.innerHTML = entries.map(function(e) { return e.html; }).join('\n');
}

// 页面加载时从Supabase渲染新动向条目
async function loadXdxFrontend() {
  var supabase = window._supabaseClient;
  if (!supabase) { setTimeout(loadXdxFrontend, 500); return; }
  try {
    var res = await supabase.from('xdx_entries').select('*').order('created_at', { ascending: false });
    renderXdxDynamic(res.data || []);
  } catch(e) {}
}
loadXdxFrontend();

// ===== 通用删除单条已发布内容 =====
async function deleteApprovedItem(id, filePath, onDone) {
  var supabase = window._supabaseClient;
  // 软删除：只将file_path设为null，这样风景线就不会显示
  await supabase.from("pending_uploads").update({ file_path: null }).eq("id", id);
  if (filePath && !filePath.startsWith("github:")) {
    await supabase.storage.from("uploads").remove([filePath]);
  }
  if (onDone) onDone();
}

// ===== 通用编辑标题 =====
async function editItemTitle(id, currentTitle, onDone) {
  var newTitle = prompt("修改标题：", currentTitle);
  if (newTitle === null || newTitle.trim() === "") return;
  var supabase = window._supabaseClient;
  await supabase.from("pending_uploads").update({ title: newTitle.trim() }).eq("id", id);
  if (onDone) onDone();
}

// 通用：从按钮找到卡片的data属性来获取id/path/title
function adminGetCard(btn) {
  return btn.closest('[data-id]');
}

async function adminEditTitle(btn) {
  var card = adminGetCard(btn);
  var id = card.dataset.id;
  var currentTitle = decodeURIComponent(card.dataset.title || "");
  var type = card.dataset.type;
  var newTitle = prompt("修改标题：", currentTitle);
  if (newTitle === null || newTitle.trim() === "") return;
  var supabase = window._supabaseClient;
  await supabase.from("pending_uploads").update({ title: newTitle.trim() }).eq("id", id);
  // 更新显示
  var titleEl = card.querySelector('.admin-mgr-title');
  if (titleEl) titleEl.textContent = newTitle.trim();
  card.dataset.title = encodeURIComponent(newTitle.trim());
}

async function adminDeleteItem(btn) {
  var card = adminGetCard(btn);
  var type = card.dataset.type || 'photo';
  var label = type === 'photo' ? '照片' : type === 'video' ? '视频' : type === 'document' ? '文件' : '启示';
  if (!confirm("确认删除此" + label + "？")) return;
  var card = adminGetCard(btn);
  var id = card.dataset.id;
  var filePath = decodeURIComponent(card.dataset.path || "");
  var supabase = window._supabaseClient;
  btn.textContent = "删除中..."; btn.disabled = true;
  
  try {
    
    // 步骤1：删除数据库记录
    var dbResult = await supabase.from("pending_uploads").delete().eq("id", id);
    
    // 步骤2：删除存储文件
    if (filePath && !filePath.startsWith("github:")) {
      
      var filesToDelete = [filePath];
      
      // 如果是照片，同时删除缿略图
      if (type === 'photo') {
        var thumbPath = generateThumbnailPath(filePath);
        filesToDelete.push(thumbPath);
      }
      
...");
      
      var storageResult = await supabase.storage.from("uploads").remove(filesToDelete);
      
      
      if (storageResult.error) {
        console.error("❌ Storage 删除出错!");
        console.error("错误类型: ", storageResult.error.message);
        alert("⚠️ 存储删除失败！\n\n错误信息：" + storageResult.error.message + "\n\n数据库记录已删除，但文件可能仍在存储中。\n\n请检查 Supabase RLS 权限设置。");
      } else {
      }
    }
    
    // 步骤3：从前台移除
    if (type === 'photo') {
      var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
      var imgUrl = filePath.startsWith("github:") ? filePath.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+filePath;
      removeAdminAlbumPhoto(imgUrl);
    }
    if (type === 'video') {
      loadVideoGallery();
    }
    
    // 步骤4：从管理列表中移除卡片
    card.style.transition = "opacity 0.3s";
    card.style.opacity = "0";
    setTimeout(function() { card.remove(); }, 300);
    
    // 步骤5：更新badge
    var badgeMap = {photo:'approvedPhotoBadge', video:'approvedVideoBadge', document:'approvedFileBadge', yuanfen:'approvedYuanfenBadge'};
    var badge = document.getElementById(badgeMap[type]);
    if (badge) { 
      var n = parseInt(badge.textContent)||1; 
      badge.textContent = Math.max(0, n-1) + (type==='photo'?' 张':' 个'); 
    }
    
    alert("✅ " + label + "已删除\n\n请查看浏览器控制台（F12）获取详细日志。");
    
  } catch (e) {
    console.error("\n❌ 删除过程出错：");
    console.error("错误信息: " + e.message);
    console.error("错误堆栈: ", e);
    alert("❌ 删除出错：" + e.message + "\n\n详情请查看浏览器控制台（F12）。");
  } finally {
    btn.textContent = "🗑 删除";
    btn.disabled = false;
  }
}

// 生成缿略图路径 - 根据原始文件路径生成对应的缿略图路径
function generateThumbnailPath(originalPath) {
  var lastDot = originalPath.lastIndexOf('.');
  if (lastDot === -1) {
    return originalPath + '_thumb.webp';
  }
  var beforeExt = originalPath.substring(0, lastDot);
  return beforeExt + '_thumb.webp';
}

// ===== 大家拍管理 =====
// ===== 大家拍动态加载 =====
async function loadVideoGallery() {
  var supabase = window._supabaseClient;
  var thumbsEl = document.getElementById("videoThumbs");
  var mainVideo = document.getElementById("mainVideo");
  var titleEl = document.getElementById("videoTitle");
  if (!supabase || !thumbsEl) return;

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "video")
    .order("uploaded_at", { ascending: true });

  // 移除loading占位
  var loadingThumb = document.getElementById("videoLoadingThumb");
  if (loadingThumb) loadingThumb.remove();

  if (result.error || !result.data || !result.data.length) {
    thumbsEl.innerHTML = '<div class="video-thumb active"><div class="video-thumb-icon">📭</div><div class="video-thumb-label">暂无视频</div></div>';
    if (titleEl) titleEl.textContent = "🎬 暂无视频";
    return;
  }

  var supabaseUrl = "https://ritglkwqpwlcjwemhfqd.supabase.co";
  window.videoList = [];
  thumbsEl.innerHTML = "";

  result.data.forEach(function(item, idx) {
    var src = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    window.videoList.push({ src: src, label: item.title || item.file_name });

    var div = document.createElement("div");
    div.className = "video-thumb" + (idx === 0 ? " active" : "");
    div.setAttribute("data-video-id", item.id);
    div.innerHTML = '<div class="video-thumb-icon">▶</div><div class="video-thumb-label">' + (item.title || item.file_name) + '</div>';
    div.onclick = (function(i, el) { return function() { switchVideo(i, el); }; })(idx, div);
    thumbsEl.appendChild(div);
  });

  // 加载第一个视频
  if (window.videoList.length > 0 && mainVideo) {
    mainVideo.querySelector("source").src = window.videoList[0].src;
    mainVideo.load();
    if (titleEl) titleEl.textContent = "🎬 " + window.videoList[0].label;
  }
}

// 管理员直接上传视频（无需审核）
async function videoAdminFilesSelected(files) {
  var supabase = window._supabaseClient;
  if (!supabase || !files.length) return;
  var prog = document.getElementById("videoAdminUploadProgress");
  var supabaseUrl = "https://ritglkwqpwlcjwemhfqd.supabase.co";
  var { data: { session } } = await supabase.auth.getSession();
  var uploader = session ? session.user.email : "admin";
  for (var i = 0; i < files.length; i++) {
    var file = files[i];
    if (prog) prog.textContent = "上传中 " + (i+1) + "/" + files.length + "：" + file.name;
    var ext = file.name.split(".").pop().toLowerCase();
    var filePath = "video/" + Date.now() + "_" + Math.random().toString(36).substr(2,6) + "." + ext;
    var uploadRes = await supabase.storage.from("uploads").upload(filePath, file, { upsert: false });
    if (uploadRes.error) { if (prog) prog.textContent = "❌ 上传失败：" + uploadRes.error.message; continue; }
    var title = file.name.replace(/\.[^.]+$/, "");
    await supabase.from("pending_uploads").insert({
      file_path: filePath, file_name: file.name, title: title,
      uploaded_by: uploader, status: "approved", file_type: "video"
    });
  }
  if (prog) prog.textContent = "✅ 上传完成（共 " + files.length + " 个）";
  loadVideoGallery();
  loadApprovedVideoManager();
}

function videoAdminFileDrop(event) {
  event.preventDefault();
  event.currentTarget.style.background = "#eef3fa";
  var files = Array.from(event.dataTransfer.files).filter(function(f){ return f.type.startsWith("video/"); });
  if (files.length) videoAdminFilesSelected(files);
}

// ===== 光影录管理（管理员专属，无需审核）=====
async function loadAdminVideoGallery() {
  var supabase = window._supabaseClient;
  var thumbsEl = document.getElementById("adminVideoThumbs");
  var mainVideo = document.getElementById("adminMainVideo");
  var titleEl = document.getElementById("adminVideoTitle");
  var container = document.getElementById("adminVideoGalleryContainer");
  var label = document.getElementById("adminVideoLabel");
  if (!supabase || !thumbsEl) return;

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "admin_video")
    .order("uploaded_at", { ascending: true });

  var loadingThumb = document.getElementById("adminVideoLoadingThumb");
  if (loadingThumb) loadingThumb.remove();

  if (result.error || !result.data || !result.data.length) {
    if (container) container.style.display = "none";
    if (label) label.style.display = "none";
    return;
  }

  if (container) container.style.display = "";
  if (label) label.style.display = "";

  var supabaseUrl = "https://ritglkwqpwlcjwemhfqd.supabase.co";
  window.adminVideoList = [];
  thumbsEl.innerHTML = "";

  result.data.forEach(function(item, idx) {
    var src = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    window.adminVideoList.push({ src: src, label: item.title || item.file_name });

    var div = document.createElement("div");
    div.className = "video-thumb" + (idx === 0 ? " active" : "");
    div.setAttribute("data-admin-video-id", item.id);
    div.innerHTML = '<div class="video-thumb-icon">▶</div><div class="video-thumb-label">' + (item.title || item.file_name) + '</div>';
    div.onclick = (function(i, el) { return function() { switchAdminVideo(i, el); }; })(idx, div);
    thumbsEl.appendChild(div);
  });

  if (window.adminVideoList.length > 0 && mainVideo) {
    mainVideo.querySelector("source").src = window.adminVideoList[0].src;
    mainVideo.load();
    if (titleEl) titleEl.textContent = "🎬 " + window.adminVideoList[0].label;
  }
}

window.switchAdminVideo = function(index, thumbEl) {
  var mainVideo = document.getElementById("adminMainVideo");
  var titleEl = document.getElementById("adminVideoTitle");
  var thumbs = document.querySelectorAll("#adminVideoThumbs .video-thumb");
  if (!mainVideo || !window.adminVideoList || !window.adminVideoList[index]) return;
  mainVideo.pause();
  mainVideo.querySelector("source").src = window.adminVideoList[index].src;
  mainVideo.load();
  if (titleEl) titleEl.textContent = "🎬 " + window.adminVideoList[index].label;
  thumbs.forEach(function(t) { t.classList.remove("active"); });
  if (thumbEl) thumbEl.classList.add("active");
};

async function adminVideoFilesSelected(files) {
  var supabase = window._supabaseClient;
  if (!supabase || !files.length) return;
  var prog = document.getElementById("adminVideoUploadProgress2");
  var supabaseUrl = "https://ritglkwqpwlcjwemhfqd.supabase.co";
  var { data: { session } } = await supabase.auth.getSession();
  var uploader = session ? session.user.email : "admin";
  for (var i = 0; i < files.length; i++) {
    var file = files[i];
    if (prog) prog.textContent = "上传中 " + (i+1) + "/" + files.length + "：" + file.name;
    var ext = file.name.split(".").pop().toLowerCase();
    var filePath = "admin_video/" + Date.now() + "_" + Math.random().toString(36).substr(2,6) + "." + ext;
    var uploadRes = await supabase.storage.from("uploads").upload(filePath, file, { upsert: false });
    if (uploadRes.error) { if (prog) prog.textContent = "❌ 上传失败：" + uploadRes.error.message; continue; }
    var title = file.name.replace(/\.[^.]+$/, "");
    await supabase.from("pending_uploads").insert({
      file_path: filePath, file_name: file.name, title: title,
      uploaded_by: uploader, status: "approved", file_type: "admin_video"
    });
  }
  if (prog) prog.textContent = "✅ 上传完成（共 " + files.length + " 个）";
  loadAdminVideoGallery();
  loadApprovedAdminVideoManager();
}

function adminVideoFileDrop2(event) {
  event.preventDefault();
  event.currentTarget.style.background = "#eef3fa";
  var files = Array.from(event.dataTransfer.files).filter(function(f){ return f.type.startsWith("video/"); });
  if (files.length) adminVideoFilesSelected(files);
}

async function loadApprovedAdminVideoManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedAdminVideoManager");
  var badge = document.getElementById("approvedAdminVideoBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "admin_video")
    .order("uploaded_at", { ascending: false });
  var items = result.data || [];
  if (badge) badge.textContent = items.length + " 个";
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无光影录</span>'; return; }
  var supabaseUrl = "https://ritglkwqpwlcjwemhfqd.supabase.co";
  var html = "";
  items.forEach(function(item) {
    var url = item.file_path.startsWith("github:") ? item.file_path.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+item.file_path;
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="admin_video">' +
      '<div class="admin-mgr-icon">🎬</div>' +
      '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">上传者：' + (item.uploaded_by||"管理员") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<a href="' + url + '" target="_blank" class="admin-mgr-edit-btn" style="text-decoration:none;">▶ 预览</a>' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="deleteAdminVideoItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function deleteAdminVideoItem(btn) {
  var card = btn.closest(".admin-mgr-card");
  var id = card.dataset.id;
  var filePath = decodeURIComponent(card.dataset.path);
  if (!confirm("确认永久删除这个视频？不可恢复。")) return;
  btn.disabled = true; btn.textContent = "删除中...";
  var supabase = window._supabaseClient;
  await supabase.from("pending_uploads").delete().eq("id", id);
  if (!filePath.startsWith("github:")) {
    await supabase.storage.from("uploads").remove([filePath]);
  }
  card.style.opacity = "0";
  setTimeout(function(){ card.remove(); }, 300);
  loadAdminVideoGallery();
  loadApprovedAdminVideoManager();
}

async function deleteAllAdminVideos() {
  if (!confirm("确认清空全部光影录？此操作不可恢复。")) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from("pending_uploads").select("id,file_path").eq("status","approved").eq("file_type","admin_video");
  if (result.error || !result.data.length) { alert("暂无视频可清空"); return; }
  var ids = result.data.map(function(i){return i.id;});
  var paths = result.data.map(function(i){return i.file_path;}).filter(function(p){return !p.startsWith("github:");});
  await supabase.from("pending_uploads").delete().in("id", ids);
  if (paths.length) await supabase.storage.from("uploads").remove(paths);
  loadAdminVideoGallery();
  loadApprovedAdminVideoManager();
  alert("✅ 已清空全部光影录（共 " + ids.length + " 个）");
}

async function loadApprovedVideoManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedVideoManager");
  var badge = document.getElementById("approvedVideoBadge");
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "video")
    .order("uploaded_at", { ascending: false });

  var items = (result.data || []);
  if (badge) badge.textContent = items.length;
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无已发布视频</span>'; return; }

  var html = '';
  items.forEach(function(item) {
    var url = item.file_path.startsWith("github:") ? item.file_path.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+item.file_path;
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    var idx = items.indexOf(item);
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="video">' +
      '<div class="admin-mgr-icon">🎬</div>' +
      '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">上传者：' + (item.uploaded_by||"匿名") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<a href="' + url + '" target="_blank" class="admin-mgr-edit-btn" style="text-decoration:none;">▶ 预览</a>' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="adminDeleteItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function deleteAllApprovedVideos() {
  if (!confirm("确认清空全部已发布视频？")) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from("pending_uploads").select("id,file_path").eq("status","approved").eq("file_type","video");
  var items = result.data || [];
  var ids = items.map(function(i){return i.id;});
  var paths = items.map(function(i){return i.file_path;}).filter(function(p){return !p.startsWith("github:");});
  if (ids.length) await supabase.from("pending_uploads").delete().in("id", ids);
  if (paths.length) await supabase.storage.from("uploads").remove(paths);
  alert("已清空 " + items.length + " 个视频");
  loadApprovedVideoManager();
  loadVideoGallery();
}

// ===== PPT/文件管理 =====
async function loadApprovedFileManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedFileManager");
  var badge = document.getElementById("approvedFileBadge");
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "document")
    .order("uploaded_at", { ascending: false });

  var items = (result.data || []);
  if (badge) badge.textContent = items.length;
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无已发布文件</span>'; return; }

  var html = '';
  items.forEach(function(item) {
    var url = item.file_path.startsWith("github:") ? item.file_path.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+item.file_path;
    var ext = (item.file_name||"").split(".").pop().toUpperCase();
    var icon = ext==="PDF" ? "📄" : (["PPT","PPTX"].includes(ext) ? "📊" : "📁");
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="document">' +
      '<div class="admin-mgr-icon">' + icon + '</div>' +
      '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">' + (item.file_name||"") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<a href="' + url + '" target="_blank" class="admin-mgr-edit-btn" style="text-decoration:none;">🔗 查看</a>' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="adminDeleteItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function deleteAllApprovedFiles() {
  if (!confirm("确认清空全部已发布文件？")) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from("pending_uploads").select("id,file_path").eq("status","approved").eq("file_type","document");
  var items = result.data || [];
  var ids = items.map(function(i){return i.id;});
  var paths = items.map(function(i){return i.file_path;}).filter(function(p){return !p.startsWith("github:");});
  if (ids.length) await supabase.from("pending_uploads").delete().in("id", ids);
  if (paths.length) await supabase.storage.from("uploads").remove(paths);
  alert("已清空 " + items.length + " 个文件");
  loadApprovedFileManager();
}

// ===== 有缘启示管理 =====
async function loadApprovedYuanfenManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedYuanfenManager");
  var badge = document.getElementById("approvedYuanfenBadge");
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "yuanfen")
    .order("uploaded_at", { ascending: false });

  var items = (result.data || []);
  if (badge) badge.textContent = items.length;
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无已发布有缘启示</span>'; return; }

  var html = '';
  items.forEach(function(item) {
    var url = supabaseUrl+"/storage/v1/object/public/uploads/"+item.file_path;
    var ext = (item.file_name||"").split(".").pop().toUpperCase();
    var isImg = ["JPG","JPEG","PNG","GIF"].includes(ext);
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="yuanfen">';
    if (isImg) {
      html += '<img class="admin-mgr-thumb" src="' + url + '" onclick="openOverlay(this.src,this.alt)" alt="' + (item.title||"") + '">' ;
    } else {
      html += '<div class="admin-mgr-icon">💌</div>';
    }
    html += '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">发布者：' + (item.uploaded_by||"匿名") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<a href="' + url + '" target="_blank" class="admin-mgr-edit-btn" style="text-decoration:none;">🔗 查看</a>' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="adminDeleteItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function deleteAllApprovedYuanfen() {
  if (!confirm("确认清空全部已发布有缘启示？")) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from("pending_uploads").select("id,file_path").eq("status","approved").eq("file_type","yuanfen");
  var items = result.data || [];
  var ids = items.map(function(i){return i.id;});
  var paths = items.map(function(i){return i.file_path;}).filter(function(p){return !p.startsWith("github:");});
  if (ids.length) await supabase.from("pending_uploads").delete().in("id", ids);
  if (paths.length) await supabase.storage.from("uploads").remove(paths);
  alert("已清空 " + items.length + " 条有缘启示");
  loadApprovedYuanfenManager();
}

// ===== 聚会吧管理（管理员直接上传，无需审核）=====
async function loadAlbumPhotoManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("albumPhotoManager");
  var badge = document.getElementById("albumPhotoBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "album")
    .order("uploaded_at", { ascending: false });
  if (result.error) { container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>'; return; }
  var items = result.data || [];
  if (badge) badge.textContent = items.length + " 张";
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无动态上传照片（静态照片在HTML中）</span>'; return; }
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var imgUrl = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="album">' +
      '<img class="admin-mgr-thumb" src="' + imgUrl + '" onclick="openOverlay(this.src,\'\')">' +
      '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">上传者：' + (item.uploaded_by||"管理员") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="deleteAlbumPhotoItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function deleteAlbumPhotoItem(btn) {
  var card = btn.closest('.admin-mgr-card');
  var id = card.dataset.id;
  var filePath = decodeURIComponent(card.dataset.path);
  if (!confirm("确认永久删除这张照片？不可恢复。")) return;
  btn.disabled = true; btn.textContent = "删除中...";
  var supabase = window._supabaseClient;
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  await supabase.from("pending_uploads").delete().eq("id", id);
  if (filePath.startsWith("github:")) {
    await deleteFromGitHubViaEdge(filePath.replace("github:", ""));
  } else {
    await supabase.storage.from("uploads").remove([filePath]);
  }
  // 从前台轮播移除
  var imgUrl = filePath.startsWith("github:") ? filePath.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+filePath;
  removeAlbumSlide(imgUrl);
  loadAlbumPhotoManager();
}

async function deleteAllAlbumPhotos() {
  if (!confirm("确认清空全部动态上传的聚会吧照片？静态照片不受影响，此操作不可恢复。")) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from("pending_uploads").select("id,file_path").eq("status","approved").eq("file_type","album");
  if (result.error || !result.data.length) { alert("暂无动态照片可清空"); return; }
  var ids = result.data.map(function(i){return i.id;});
  var paths = result.data.map(function(i){return i.file_path;});
  await supabase.from("pending_uploads").delete().in("id", ids);
  var staticPaths = paths.filter(function(p){return !p.startsWith("github:");});
  if (staticPaths.length) await supabase.storage.from("uploads").remove(staticPaths);
  for (var p of paths.filter(function(p){return p.startsWith("github:");})) {
    await deleteFromGitHubViaEdge(p.replace("github:",""));
  }
  // 清空前台动态slides
  var track = document.getElementById("slideshowTrack");
  if (track) {
    track.querySelectorAll('.slide[data-dynamic="1"]').forEach(function(s){s.remove();});
    reinitMainSlideshow();
  }
  loadAlbumPhotoManager();
  alert("✅ 已清空全部动态上传照片（共 " + ids.length + " 张）");
}

// 管理员直接上传照片到聚会吧（无需审核）
async function albumAdminFilesSelected(files) {
  var supabase = window._supabaseClient;
  if (!supabase || !files.length) return;
  var prog = document.getElementById("albumUploadProgress");
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var { data: { session } } = await supabase.auth.getSession();
  var uploader = session ? session.user.email : "admin";
  for (var i = 0; i < files.length; i++) {
    var file = files[i];
    if (prog) prog.textContent = "上传中 " + (i+1) + "/" + files.length + "：" + file.name;
    var ext = file.name.split(".").pop().toLowerCase();
    var filePath = "album/" + Date.now() + "_" + Math.random().toString(36).substr(2,6) + "." + ext;
    var uploadRes = await supabase.storage.from("uploads").upload(filePath, file, { upsert: false });
    if (uploadRes.error) { if (prog) prog.textContent = "❌ 上传失败：" + uploadRes.error.message; continue; }
    var title = file.name.replace(/\.[^.]+$/, "");
    await supabase.from("pending_uploads").insert({
      file_path: filePath, file_name: file.name, title: title,
      uploaded_by: uploader, status: "approved", file_type: "album"
    });
    // 追加到前台轮播
    var imgUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + filePath;
    appendAlbumSlide(imgUrl, title);
  }
  if (prog) prog.textContent = "✅ 上传完成（共 " + files.length + " 张）";
  loadAlbumPhotoManager();
}

function albumAdminFileDrop(event) {
  event.preventDefault();
  event.currentTarget.style.background = '#eef3fa';
  var files = event.dataTransfer.files;
  var imageFiles = Array.from(files).filter(function(f){return f.type.startsWith("image/");});
  if (imageFiles.length) albumAdminFilesSelected(imageFiles);
}

// 向前台聚会吧轮播追加一张动态照片（管理员上传后实时追加）
function appendAlbumSlide(imgUrl, title) {
  var track = document.getElementById("slideshowTrack");
  if (!track) return;
  var div = document.createElement("div");
  div.className = "slide";
  div.setAttribute("data-dynamic", "1");
  div.setAttribute("data-url", imgUrl);
  div.innerHTML = '<img src="' + imgUrl + '" alt="' + (title||"") + '" onclick="openOverlay(this.src, this.alt)">';
  track.appendChild(div);
  reinitMainSlideshow();
}

// 从前台聚会吧轮播移除指定url的slide
function removeAlbumSlide(imgUrl) {
  var track = document.getElementById("slideshowTrack");
  if (!track) return;
  track.querySelectorAll('.slide[data-dynamic="1"]').forEach(function(slide) {
    if (slide.dataset.url === imgUrl) slide.remove();
  });
  reinitMainSlideshow();
}

// 重新初始化前台主轮播（聚会吧）
function reinitMainSlideshow() {
  if (typeof window.initMainSlideshow === 'function') {
    window.initMainSlideshow();
  }
}

// 页面加载时动态加载聚会吧全部照片
async function loadAlbumPhotosToSlideshow() {
  var supabase = window._supabaseClient;
  var track = document.getElementById("slideshowTrack");
  if (!supabase || !track) return;
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status","approved").eq("file_type","album")
    .order("uploaded_at", { ascending: true });
  // 移除loading占位
  var loadingSlide = document.getElementById("albumLoadingSlide");
  if (loadingSlide) loadingSlide.remove();
  if (result.error || !result.data || !result.data.length) {
    // 无照片时显示空状态
    var empty = document.createElement("div");
    empty.className = "slide active";
    empty.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:260px;color:#aaa;font-size:14px;">📷 相册暂无照片，管理员可在后台上传</div>';
    track.appendChild(empty);
    reinitMainSlideshow();
    return;
  }
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  result.data.forEach(function(item, idx) {
    var imgUrl = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:","")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var div = document.createElement("div");
    div.className = "slide" + (idx === 0 ? " active" : "");
    div.setAttribute("data-dynamic", "1");
    div.setAttribute("data-url", imgUrl);
    div.innerHTML = '<img src="' + imgUrl + '" alt="' + (item.title||"") + '" onclick="openOverlay(this.src, this.alt)">';
    track.appendChild(div);
  });
  reinitMainSlideshow();
}

async function loadApprovedPhotoManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedPhotoManager");
  var badge = document.getElementById("approvedPhotoBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "approved")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data.filter(function(i) { return !i.file_type || i.file_type === "image"; });

  // 逐一检测图片是否可访问，过滤失效记录并删除数据库条目
  var validItems = [];
  var brokenIds = [];
  await Promise.all(items.map(async function(item) {
    var imgUrl = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    try {
      var resp = await fetch(imgUrl, { method: "HEAD", cache: "no-cache" });
      if (resp.ok) {
        validItems.push(item);
      } else {
        brokenIds.push(item.id);
      }
    } catch(e) {
      brokenIds.push(item.id);
    }
  }));

  // 批量删除失效记录
  if (brokenIds.length > 0) {
    await supabase.from("pending_uploads").delete().in("id", brokenIds);
  }

  // 按上传时间排序
  validItems.sort(function(a, b) { return new Date(b.uploaded_at) - new Date(a.uploaded_at); });

  if (badge) badge.textContent = validItems.length > 0 ? validItems.length + " 张" : "0 张";

  if (!validItems.length) {
    container.innerHTML = '<span style="color:#aaa;">风景线暂无照片</span>';
    return;
  }

  var html = '';
  validItems.forEach(function(item) {
    var imgUrl = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString("zh-CN") : "";
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||"") + '" data-type="photo">' +
      '<img class="admin-mgr-thumb" src="' + imgUrl + '" onclick="openOverlay(\'' + imgUrl + '\',\'\')">' +
      '<div class="admin-mgr-body">' +
        '<div class="admin-mgr-title">' + (item.title||"未命名") + '</div>' +
        '<div class="admin-mgr-meta">上传者：' + (item.uploaded_by||"匿名") + ' · ' + date + '</div>' +
        '<div class="admin-mgr-actions">' +
          '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
          '<button class="admin-mgr-del-btn" onclick="adminDeleteItem(this)">🗑 删除</button>' +
        '</div>' +
      '</div></div>';
  });
  container.innerHTML = html || '<span style="color:#aaa;">暂无照片</span>';
}

// 通过 Edge Function 删除 GitHub 上的文件
const GITHUB_DELETE_EDGE_URL = "https://ritglkwqpwlcjwemhfqd.supabase.co/functions/v1/github-upload";
async function deleteFromGitHubViaEdge(githubUrl) {
  var supabase = window._supabaseClient;
  var { data: { session } } = await supabase.auth.getSession();
  if (!session) return;
  try {
    await fetch(GITHUB_DELETE_EDGE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + session.access_token
      },
      body: JSON.stringify({ action: "delete", url: githubUrl })
    });
  } catch(e) {
    console.warn("GitHub 文件删除失败（不影响数据库删除）：", e);
  }
}

async function deleteApprovedPhotoItem(id, filePath) {
  if (!confirm("确认从风景线永久删除这张照片？\n将同时从数据库和 GitHub 彻底删除，不可恢复。")) return;
  var supabase = window._supabaseClient;
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  // 1. 删数据库记录
  await supabase.from("pending_uploads").delete().eq("id", id);

  // 2. 删文件（GitHub 或 Supabase Storage）
  if (filePath.startsWith("github:")) {
    await deleteFromGitHubViaEdge(filePath.replace("github:", ""));
  } else {
    await supabase.storage.from("uploads").remove([filePath]);
  }

  // 3. 从轮播移除
  var imgUrl = filePath.startsWith("github:") ? filePath.replace("github:","") : supabaseUrl+"/storage/v1/object/public/uploads/"+filePath;
  removeAdminAlbumPhoto(imgUrl);
  loadApprovedPhotoManager();
}

async function deleteAllApprovedPhotos() {
  if (!confirm("确认永久清空风景线全部照片？\n将同时从数据库和 GitHub 彻底删除，此操作不可恢复。")) return;
  var supabase = window._supabaseClient;

  
  // 先查出所有 approved 图片记录
  var result = await supabase
    .from("pending_uploads")
    .select("id,file_path,file_type")
    .eq("status", "approved");

  if (result.error || !result.data) { 
    console.error("[批量删除] 获取列表失败: ", result.error);
    alert("获取列表失败: " + (result.error ? result.error.message : "未知错误")); 
    return; 
  }

  var items = result.data.filter(function(i) { return !i.file_type || i.file_type === "image"; });

  if (items.length === 0) {
    alert("没有找到要删除的照片");
    return;
  }

  // 【新增】标记所有照片为已删除（本地localStorage）
  var deletedList = [];
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  items.forEach(function(item) {
    var url = item.file_path.startsWith("github:")
      ? item.file_path.replace("github:", "")
      : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    deletedList.push(url);
  });
  localStorage.setItem('deletedAdminPhotos', JSON.stringify(deletedList));

  // 收集各类路径 - 包括缿略图
  var storagePaths = [];
  var githubUrls = [];
  
  items.forEach(function(item) {
    if (item.file_path.startsWith("github:")) {
      githubUrls.push(item.file_path.replace("github:", ""));
    } else {
      storagePaths.push(item.file_path);
      // 为每个照片添加对应的缿略图路径
      var thumbPath = generateThumbnailPath(item.file_path);
      storagePaths.push(thumbPath);
    }
  });


  // 步骤1：删除数据库记录
  var ids = items.map(function(i){return i.id;});
  if (ids.length) {
    var dbDeleteResult = await supabase.from("pending_uploads").delete().in("id", ids);
  }

  // 步骤2：删除 Supabase Storage
  if (storagePaths.length) {
    var storageDeleteResult = await supabase.storage.from("uploads").remove(storagePaths);
    
    if (storageDeleteResult.error) {
      console.error("[错误] Storage 删除失败: ", storageDeleteResult.error);
      alert("⚠️ Storage 文件删除失败: " + storageDeleteResult.error.message);
    }
  }

  // 步骤3：删除 GitHub 文件（逐个调用 Edge Function）
  for (var i = 0; i < githubUrls.length; i++) {
 + "/" + githubUrls.length + ": " + githubUrls[i]);
    await deleteFromGitHubViaEdge(githubUrls[i]);
  }

  // 步骤4：清空风景线轮播
  var track = document.getElementById("adminSlideshowTrack");
  var dots  = document.getElementById("adminSlideDots");
  var section = document.getElementById("adminAlbumSection");
  if (track) track.innerHTML = "";
  if (dots)  dots.innerHTML = "";
  clearInterval(adminSlide.timer);
  adminSlide.current = 0; adminSlide.total = 0;
  if (section) section.style.display = "none";

  alert("✅ 已永久清空风景线及所有缿略图（共 " + items.length + " 张）\n\n请查看浏览器控制台（F12）获取详细日志。");
  loadApprovedPhotoManager();
}

// 从风景线轮播中移除指定 URL 的 slide
function removeAdminAlbumPhoto(imgSrc) {
  var track = document.getElementById("adminSlideshowTrack");
  var dots  = document.getElementById("adminSlideDots");
  var counter = document.getElementById("adminSlideCounter");
  var section = document.getElementById("adminAlbumSection");
  if (!track) return;

  var slides = Array.from(track.querySelectorAll(".slide"));
  var idx = -1;
  slides.forEach(function(slide, i) {
    var img = slide.querySelector("img");
    if (img && img.src === imgSrc) idx = i;
  });
  if (idx === -1) return;

  // 移除 slide 和对应圆点
  track.children[idx].remove();
  if (dots && dots.children[idx]) dots.children[idx].remove();

  adminSlide.total--;

  if (adminSlide.total === 0) {
    // 没有照片了，隐藏整个区块
    clearInterval(adminSlide.timer);
    if (section) section.style.display = "none";
    // 【新增】清空管理员审核列表中的缩略图
    var adminList = document.getElementById("pendingUploadsList");
    if (adminList) {
      adminList.innerHTML = '<span style="color:#aaa;">暂无待审核照片</span>';
    }
    // 【新增】重新加载待审核列表
    if (typeof loadPendingUploads === 'function') {
      loadPendingUploads();
    }
    // 【新增】重新加载已批准列表（显示已删除后的列表）
    if (typeof loadApprovedPhotoManager === 'function') {
      loadApprovedPhotoManager();
    }
    return;
  }

  // 重建圆点的 onclick（索引已变）
  Array.from(dots.children).forEach(function(dot, i) {
    dot.onclick = function() { adminGoTo(i); adminResetAuto(); };
  });

  // 修正 current 指针
  if (adminSlide.current >= adminSlide.total) adminSlide.current = adminSlide.total - 1;

  // 确保有一张是 active
  var remaining = track.querySelectorAll(".slide");
  remaining.forEach(function(s) { s.classList.remove("active"); });
  Array.from(dots.children).forEach(function(d) { d.classList.remove("active"); });
  remaining[adminSlide.current].classList.add("active");
  if (dots.children[adminSlide.current]) dots.children[adminSlide.current].classList.add("active");
  if (counter) counter.textContent = (adminSlide.current + 1) + " / " + adminSlide.total;
}

// ===== 审核功能 =====
async function loadPendingUploads() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingUploadsList");
  var badge = document.getElementById("pendingBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "pending")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data.filter(function(item) { return !item.file_type || item.file_type === "image"; });
  if (badge) badge.textContent = items.length > 0 ? items.length + " 条" : "";

  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无待审核照片</span>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    html += '<div style="border:1px solid #f0c060; border-radius:8px; padding:12px; margin-bottom:12px; background:#fffbf0;">' +
      '<div style="display:flex; gap:12px; align-items:flex-start;">' +
      '<img src="' + pubUrl + '" style="width:100px; height:80px; object-fit:cover; border-radius:6px; border:1px solid #ddd; cursor:pointer;" onclick="openOverlay(\'' + pubUrl + '\', \'' + item.title + '\')">' +
      '<div style="flex:1;">' +
      '<div style="font-weight:bold; font-size:14px; color:#333; margin-bottom:4px;">📌 ' + item.title + '</div>' +
      '<div style="font-size:12px; color:#888;">上传者：' + (item.uploaded_by || '匿名') + '</div>' +
      '<div style="font-size:12px; color:#888;">时间：' + date + '</div>' +
      '<div style="font-size:12px; color:#888; word-break:break-all;">文件：' + item.file_name + '</div>' +
      '</div></div>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approvePhoto(\'' + item.id + '\', \'' + pubUrl + '\', \'' + item.title + '\')" style="flex:1; padding:8px; background:#003366; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">✅ 批准加入风景线</button>' +
      '<button onclick="rejectPendingItem(\'' + item.id + '\', \'' + item.file_path + '\')" style="flex:1; padding:8px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">❌ 拒绝删除</button>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

// ===== GitHub 上传核心函数（通过 Supabase Edge Function，Token 在服务端）=====
const EDGE_FUNCTION_URL = "https://ritglkwqpwlcjwemhfqd.supabase.co/functions/v1/github-upload";

// 调用服务端 Edge Function 完成上传，前端不持有任何 Token
async function uploadToGitHubViaEdge(pendingId, folder) {
  var supabase = window._supabaseClient;

  // 获取当前用户的 JWT，用于服务端鉴权
  var { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error("未登录，请先登录后再操作");

  var resp = await fetch(EDGE_FUNCTION_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + session.access_token
    },
    body: JSON.stringify({ pendingId: pendingId, folder: folder })
  });

  // 尝试解析响应体（无论成功失败都尝试）
  var result;
  try {
    result = await resp.json();
  } catch (parseErr) {
    throw new Error("Edge Function 返回非 JSON（HTTP " + resp.status + "）：" + resp.statusText);
  }

  if (!resp.ok || result.error) {
    var detail = result.error || result.message || JSON.stringify(result);
    throw new Error("HTTP " + resp.status + " - " + detail);
  }
  return result.url; // 返回 GitHub 文件的公开 URL
}

async function approvePhoto(id, pubUrl, title) {
  if (!confirm("批准此照片？")) return;
  var btn = event.target;
  btn.textContent = "处理中..."; btn.disabled = true;

  try {
    // ✅ 直接使用Supabase URL，不调用GitHub
    var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
    var fileUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + pubUrl;
    
    var supabase = window._supabaseClient;
    await supabase.from("pending_uploads").update({ status: "approved" }).eq("id", id);
    
    addSlideToShow(fileUrl, title);
    alert("已批准！照片已加入风景线。");
    loadPendingUploads();
  } catch(e) {
    alert("失败：" + e.message);
    btn.textContent = "批准加入风景线"; btn.disabled = false;
  }
}

async function approveVideo(id, pubUrl, title) {
  if (!confirm("批准此视频？")) return;
  var btn = event.target;
  btn.textContent = "处理中..."; btn.disabled = true;

  try {
    // ✅ 直接使用Supabase URL，不调用GitHub
    var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
    var fileUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + pubUrl;
    
    var supabase = window._supabaseClient;
    await supabase.from("pending_uploads").update({ status: "approved" }).eq("id", id);

    addVideoThumb(fileUrl, title);
    alert("已批准！视频已加入视频区。");
    loadPendingVideos();
  } catch(e) {
    alert("失败：" + e.message);
    btn.textContent = "批准加入视频区"; btn.disabled = false;
  }
}

async function approvePpt(id, pubUrl, title, fileName) {
  if (!confirm("批准此文件？")) return;
  var btn = event.target;
  btn.textContent = "处理中..."; btn.disabled = true;

  try {
    // ✅ 直接使用Supabase URL，不调用GitHub
    var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
    var fileUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + pubUrl;
    
    var supabase = window._supabaseClient;
    await supabase.from("pending_uploads").update({ status: "approved" }).eq("id", id);

    addPptFileEntry(fileUrl, title, fileName);
    alert("已批准！文件已发布到文件区。");
    loadPendingPpts();
  } catch(e) {
    alert("失败：" + e.message);
    btn.textContent = "批准发布到PPT区"; btn.disabled = false;
  }
}

// ===== 通用拒绝函数（照片/视频/文件共用） =====

// ===== 管理员风景线（幻灯片）=====
var adminSlide = {
  current: 0,
  total: 0,
  timer: null
};

function adminGoTo(n) {
  var track = document.getElementById("adminSlideshowTrack");
  var dots  = document.getElementById("adminSlideDots");
  var counter = document.getElementById("adminSlideCounter");
  if (!track || adminSlide.total === 0) return;

  var slides = track.querySelectorAll(".slide");
  slides[adminSlide.current].classList.remove("active");
  if (dots.children[adminSlide.current]) dots.children[adminSlide.current].classList.remove("active");

  adminSlide.current = (n + adminSlide.total) % adminSlide.total;

  slides[adminSlide.current].classList.add("active");
  if (dots.children[adminSlide.current]) dots.children[adminSlide.current].classList.add("active");
  if (counter) counter.textContent = (adminSlide.current + 1) + " / " + adminSlide.total;
}

function adminStartAuto() {
  clearInterval(adminSlide.timer);
  adminSlide.timer = setInterval(function() { adminGoTo(adminSlide.current + 1); }, 4000);
}

function adminResetAuto() {
  clearInterval(adminSlide.timer);
  adminStartAuto();
}

// 添加单张照片到管理员风景线轮播
function addAdminAlbumPhoto(imgSrc, altText) {
  var track = document.getElementById("adminSlideshowTrack");
  var dots  = document.getElementById("adminSlideDots");
  var counter = document.getElementById("adminSlideCounter");
  var section = document.getElementById("adminAlbumSection");
  if (!track) return;

  var isFirst = (adminSlide.total === 0);

  // 创建 slide
  var slide = document.createElement("div");
  slide.className = "slide" + (isFirst ? " active" : "");
  slide.innerHTML = '<img src="' + imgSrc + '" alt="' + (altText || "照片") + '" onclick="openOverlay(this.src, this.alt)" style="width:100%;max-height:480px;object-fit:contain;cursor:zoom-in;display:block;margin:0 auto;background:#000;">';
  
  // 加入图片加载错误处理
  var img = slide.querySelector('img');
  if (img) {
    img.onerror = function() {
      // 移除失败的slide和对应的dot
      slide.remove();
      if (dots && dots.children[adminSlide.total - 1]) {
        dots.children[adminSlide.total - 1].remove();
      }
      // 重新计数
      adminSlide.total--;
      if (counter) counter.textContent = (adminSlide.current + 1) + " / " + adminSlide.total;
    };
  }
  
  track.appendChild(slide);

  // 创建圆点
  if (dots) {
    var dot = document.createElement("span");
    dot.className = "slide-dot" + (isFirst ? " active" : "");
    (function(idx) {
      dot.onclick = function() { adminGoTo(idx); adminResetAuto(); };
    })(adminSlide.total);
    dots.appendChild(dot);
  }

  adminSlide.total++;
  if (counter) counter.textContent = (adminSlide.current + 1) + " / " + adminSlide.total;

  // 首次出现时显示区块并绑定按钮
  if (isFirst) {
    if (section) section.style.display = "";

    var prevBtn = document.getElementById("adminSlidePrev");
    var nextBtn = document.getElementById("adminSlideNext");
    if (prevBtn) prevBtn.onclick = function() { adminGoTo(adminSlide.current - 1); adminResetAuto(); };
    if (nextBtn) nextBtn.onclick = function() { adminGoTo(adminSlide.current + 1); adminResetAuto(); };

    // 触摸滑动支持
    var container = document.getElementById("adminSlideshowContainer");
    if (container) {
      var touchStartX = 0;
      container.addEventListener("touchstart", function(e) {
        touchStartX = e.touches[0].clientX;
      }, { passive: true });
      container.addEventListener("touchend", function(e) {
        var diff = touchStartX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 40) {
          adminGoTo(diff > 0 ? adminSlide.current + 1 : adminSlide.current - 1);
          adminResetAuto();
        }
      }, { passive: true });
    }

    adminStartAuto();
  }
}

// 保持旧名称兼容（批准照片后调用）
function addSlideToShow(imgSrc, altText) {
  addAdminAlbumPhoto(imgSrc, altText);
}

// 页面加载时从 Supabase 读取已批准的管理员上传照片
async function loadApprovedAdminPhotos() {
  var supabase = window._supabaseClient;
  if (!supabase) return;

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';

  // 直接在数据库查询中排除file_path为null的记录
  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "approved")
    .eq("file_type", "image")
    .neq("file_path", null)
    .order("uploaded_at", { ascending: false });

  if (result.error || !result.data) {
    return;
  }

  // 二次过滤：确保file_path是有效的字符串
  var items = result.data.filter(function(i) { 
    return i.file_type === "image" && 
           i.file_path &&  
           typeof i.file_path === 'string' &&
           i.file_path.trim() !== "";
  });
  
  
  if (!items.length) {
    var section = document.getElementById("adminAlbumSection");
    if (section) section.style.display = "none";
    return;
  }

  // 直接加载所有有效的照片
  items.forEach(function(item) {
    var imgUrl;
    if (item.file_path.startsWith("github:")) {
      imgUrl = item.file_path.replace("github:", "");
    } else {
      imgUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    }
    
    addAdminAlbumPhoto(imgUrl, item.title || "");
  });
}

// ===== 用户上传功能 =====
var userPendingFile = null;

function toggleUserUpload() {
  var box = document.getElementById("userUploadBox");
  if (box) box.style.display = box.style.display === "none" ? "block" : "none";
}

function userFileDrop(e) {
  e.preventDefault();
  document.getElementById("userDropZone").style.background = "#eef3fa";
  var files = e.dataTransfer.files;
  if (files.length) userFileSelected(files);
}

function userFileSelected(files) {
  if (!files.length) return;
  var file = files[0];
  if (!file.type.startsWith("image/")) {
    alert("请选择图片文件（JPG、PNG 等）");
    return;
  }
  userPendingFile = file;
  var preview = document.getElementById("userFilePreview");
  var previewImg = document.getElementById("userPreviewImg");
  var previewName = document.getElementById("userPreviewName");
  if (preview && previewImg) {
    var reader = new FileReader();
    reader.onload = function(e) { previewImg.src = e.target.result; };
    reader.readAsDataURL(file);
    preview.style.display = "block";
    if (previewName) previewName.textContent = file.name;
  }
}

async function submitUserPhoto() {
  var supabase = window._supabaseClient;
  if (!supabase) { alert("请先登录网站"); return; }
  if (!userPendingFile) { alert("请先选择图片"); return; }

  var title = document.getElementById("userPhotoTitle").value.trim();
  if (!title) { alert("请填写照片标题/说明"); return; }

  var msg = document.getElementById("userUploadMsg");
  msg.textContent = "上传中...";
  msg.style.color = "#003366";

  var imgExt = userPendingFile.name.split(".").pop().toLowerCase();
  var safeImgName = Date.now() + "." + imgExt;
  var filePath = "pending/" + safeImgName;
  
  // 【修改】先上传到Supabase（临时），再转存到GitHub
  var uploadResult = await supabase.storage.from("uploads").upload(filePath, userPendingFile, { upsert: true });

  if (uploadResult.error) {
    msg.textContent = "上传失败：" + uploadResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  // 获取当前用户信息
  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : "匿名";

  // 【修改】先写入pending记录，然后转存到GitHub
  var dbResult = await supabase.from("pending_uploads").insert({
    file_path: filePath,
    file_name: userPendingFile.name,
    title: title,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "image"
  }).select().single();

  if (dbResult.error) {
    msg.textContent = "提交失败：" + dbResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var pendingId = dbResult.data.id;

  // 【新增】转存到GitHub
  msg.textContent = "转存到GitHub中...";
  msg.style.color = "#c07000";
  
  try {
    var ghUrl = await uploadToGitHubViaEdge(pendingId, "images");
    msg.textContent = "✅ 上传成功！已保存到GitHub，等待管理员审核。";
    msg.style.color = "green";
    sendResendNotification('照片', title, uploadedBy);
  } catch (e) {
    // 转存失败时：保留 pending 记录（等待管理员审核），提示用户
    var errMsg = e.message || "未知错误";
    console.error("[用户投稿 GitHub转存失败]", errMsg);
    msg.textContent = "⚠️ 已提交审核，等待管理员审核（GitHub转存失败：" + errMsg + "）";
    msg.style.color = "#c07000";
  }

  userPendingFile = null;
  document.getElementById("userPhotoTitle").value = "";
  document.getElementById("userFilePreview").style.display = "none";
  document.getElementById("userFileInput").value = "";
}

// ===== Q&A 提问上传功能 =====
function toggleQAUpload() {
  var box = document.getElementById("qaUploadBox");
  if (box) box.style.display = box.style.display === "none" ? "block" : "none";
}

async function submitQAQuestion() {
  var supabase = window._supabaseClient;
  if (!supabase) { alert("请先登录网站"); return; }

  var question = document.getElementById("qaQuestion").value.trim();
  var context = document.getElementById("qaContext").value.trim();
  var name = document.getElementById("qaName").value.trim();

  if (!question) { alert("请输入问题"); return; }
  if (!name) { alert("请填写您的名字或昵称"); return; }

  var msg = document.getElementById("qaUploadMsg");
  msg.textContent = "提交中...";
  msg.style.color = "#003366";

  // 获取当前用户信息
  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : name;

  // 插入pending_uploads表中，file_type为"qa_question"
  var dbResult = await supabase.from("pending_uploads").insert({
    file_name: question,
    title: question,
    file_path: "qa:" + name,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "qa_question",
    metadata: JSON.stringify({
      context: context,
      submitter_name: name,
      submitted_at: new Date().toISOString()
    })
  }).select().single();

  if (dbResult.error) {
    msg.textContent = "提交失败：" + dbResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  msg.textContent = "✅ 问题已提交！感谢您的提问，管理员将审核后添加到Q&A部分。";
  msg.style.color = "green";
  sendResendNotification('Q&A', question, uploadedBy);

  setTimeout(function() {
    document.getElementById("qaQuestion").value = "";
    document.getElementById("qaContext").value = "";
    document.getElementById("qaName").value = "";
    document.getElementById("qaUploadBox").style.display = "none";
    msg.textContent = "";
  }, 2000);
}

// ===== 用户上传视频功能 =====
var userPendingVideo = null;

function toggleVideoUpload() {
  var box = document.getElementById("videoUploadBox");
  if (box) box.style.display = box.style.display === "none" ? "block" : "none";
}

function videoFileDrop(e) {
  e.preventDefault();
  document.getElementById("videoDropZone").style.background = "#eef3fa";
  var files = e.dataTransfer.files;
  if (files.length) videoFileSelected(files);
}

function videoFileSelected(files) {
  if (!files.length) return;
  var file = files[0];
  if (!file.type.startsWith("video/")) {
    alert("请选择视频文件（MP4、MOV 等）");
    return;
  }
  if (file.size > 500 * 1024 * 1024) {
    alert("视频文件不能超过 500MB");
    return;
  }
  userPendingVideo = file;
  var preview = document.getElementById("videoFilePreview");
  if (preview) {
    document.getElementById("videoPreviewNameText").textContent = file.name;
    var size = file.size > 1024*1024 ? (file.size/1024/1024).toFixed(1)+"MB" : (file.size/1024).toFixed(0)+"KB";
    document.getElementById("videoPreviewSize").textContent = "文件大小：" + size;
    preview.style.display = "block";
  }
}

async function submitUserVideo(btn) {
  var container = btn.closest('.user-upload-inner');
  var supabase = window._supabaseClient;
  var msg = container.querySelector('#videoUploadMsg') || container.querySelector('p[id$="UploadMsg"]') || container.querySelector('p');
  if (!supabase) {
    msg.textContent = "请先登录网站";
    msg.style.color = "crimson";
    return;
  }
  if (!userPendingVideo) {
    msg.textContent = "请先选择视频文件";
    msg.style.color = "crimson";
    return;
  }

  var titleInput = container.querySelector('input[type="text"]');
  var title = titleInput ? titleInput.value.trim() : '';
  if (!title) {
    msg.textContent = "请填写视频标题/说明";
    msg.style.color = "crimson";
    return;
  }
  msg.textContent = "上传中，请稍候...";
  msg.style.color = "#003366";

  var videoExt = userPendingVideo.name.split(".").pop().toLowerCase();
  var safeVideoName = Date.now() + "." + videoExt;
  var filePath = "pending_videos/" + safeVideoName;
  var uploadResult = await supabase.storage.from("uploads").upload(filePath, userPendingVideo, { upsert: true });

  if (uploadResult.error) {
    msg.textContent = "上传失败：" + uploadResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : "匿名";

  var dbResult = await supabase.from("pending_uploads").insert({
    file_path: filePath,
    file_name: userPendingVideo.name,
    title: title,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "video"
  }).select().single();

  if (dbResult.error) {
    msg.textContent = "提交失败：" + dbResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var pendingId = dbResult.data.id;

  // 转存到GitHub
  msg.textContent = "转存到GitHub中...";
  msg.style.color = "#c07000";

  try {
    await uploadToGitHubViaEdge(pendingId, "videos");
    msg.textContent = "✅ 上传成功！已保存到GitHub，等待管理员审核。";
    msg.style.color = "green";
  } catch (e) {
    var errMsg = e.message || "未知错误";
    console.error("[视频投稿 GitHub转存失败]", errMsg);
    msg.textContent = "⚠️ 已提交审核，等待管理员审核（GitHub转存失败：" + errMsg + "）";
    msg.style.color = "#c07000";
  }

  sendResendNotification('视频', title, uploadedBy);
  userPendingVideo = null;
  if (titleInput) titleInput.value = "";
  var preview = container.querySelector('#videoFilePreview');
  if (preview) preview.style.display = "none";
  var fileInput = container.querySelector('input[type="file"]');
  if (fileInput) fileInput.value = "";
}

// ===== 用户上传PPT/文件功能 =====
var userPendingPpt = null;

function togglePptUpload() {
  var box = document.getElementById("pptUploadBox");
  if (box) box.style.display = box.style.display === "none" ? "block" : "none";
}

function pptFileDrop(e) {
  e.preventDefault();
  document.getElementById("pptDropZone").style.background = "#eef3fa";
  var files = e.dataTransfer.files;
  if (files.length) pptFileSelected(files);
}

function pptFileSelected(files) {
  if (!files.length) return;
  var file = files[0];
  var allowed = ["application/pdf", "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"];
  var ext = file.name.split(".").pop().toLowerCase();
  var allowedExt = ["pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx"];
  if (!allowedExt.includes(ext)) {
    alert("请选择支持的文件格式：PDF、PPT、PPTX、DOC、DOCX 等");
    return;
  }
  if (file.size > 100 * 1024 * 1024) {
    alert("文件不能超过 100MB");
    return;
  }
  userPendingPpt = file;
  var preview = document.getElementById("pptFilePreview");
  if (preview) {
    document.getElementById("pptPreviewNameText").textContent = file.name;
    var size = file.size > 1024*1024 ? (file.size/1024/1024).toFixed(1)+"MB" : (file.size/1024).toFixed(0)+"KB";
    document.getElementById("pptPreviewSize").textContent = "文件大小：" + size;
    preview.style.display = "block";
  }
}

async function submitPptFile() {
  var supabase = window._supabaseClient;
  var msg = document.getElementById("pptUploadMsg");
  if (!supabase) {
    msg.textContent = "请先登录网站";
    msg.style.color = "crimson";
    return;
  }
  if (!userPendingPpt) {
    msg.textContent = "请先选择文件";
    msg.style.color = "crimson";
    return;
  }

  var title = document.getElementById("pptFileTitle").value.trim();
  if (!title) {
    msg.textContent = "请填写文件标题/说明";
    msg.style.color = "crimson";
    return;
  }
  msg.textContent = "上传中，请稍候...";
  msg.style.color = "#003366";

  var ext = userPendingPpt.name.split(".").pop().toLowerCase();
  var safeFileName = Date.now() + "." + ext;
  var filePath = "pending_ppts/" + safeFileName;
  var uploadResult = await supabase.storage.from("uploads").upload(filePath, userPendingPpt, { upsert: true });

  if (uploadResult.error) {
    msg.textContent = "上传失败：" + uploadResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : "匿名";

  var dbResult = await supabase.from("pending_uploads").insert({
    file_path: filePath,
    file_name: userPendingPpt.name,
    title: title,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "document"
  }).select().single();

  if (dbResult.error) {
    msg.textContent = "提交失败：" + dbResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var pendingId = dbResult.data.id;

  msg.textContent = "转存到GitHub中...";
  msg.style.color = "#c07000";

  try {
    await uploadToGitHubViaEdge(pendingId, "documents");
    msg.textContent = "✅ 上传成功！已保存到GitHub，等待管理员审核。";
    msg.style.color = "green";
  } catch (e) {
    console.error("[文件投稿 GitHub转存失败]", e.message);
    msg.textContent = "⚠️ 已提交审核，等待管理员审核（GitHub转存失败：" + e.message + "）";
    msg.style.color = "#c07000";
  }

  sendResendNotification('文件', title, uploadedBy);
  userPendingPpt = null;
  document.getElementById("pptFileTitle").value = "";
  document.getElementById("pptFilePreview").style.display = "none";
  document.getElementById("pptFileInput").value = "";
}

// ===== 管理员：审核待审核视频 =====
async function loadPendingVideos() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingVideosList");
  var badge = document.getElementById("pendingVideoBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "pending")
    .eq("file_type", "video")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data;
  if (badge) badge.textContent = items.length > 0 ? items.length + " 条" : "";

  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无待审核视频</span>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    html += '<div style="border:1px solid #90d060; border-radius:8px; padding:12px; margin-bottom:12px; background:#f5fff0;">' +
      '<div style="display:flex; gap:12px; align-items:flex-start;">' +
      '<div style="width:100px; height:80px; background:#111; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:32px; flex-shrink:0;">🎬</div>' +
      '<div style="flex:1;">' +
      '<div style="font-weight:bold; font-size:14px; color:#333; margin-bottom:4px;">📌 ' + item.title + '</div>' +
      '<div style="font-size:12px; color:#888;">上传者：' + (item.uploaded_by || '匿名') + '</div>' +
      '<div style="font-size:12px; color:#888;">时间：' + date + '</div>' +
      '<div style="font-size:12px; color:#888; word-break:break-all;">文件：' + item.file_name + '</div>' +
      '<a href="' + pubUrl + '" target="_blank" style="font-size:12px; color:#003366;">🔗 预览视频</a>' +
      '</div></div>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approveVideo(\'' + item.id + '\', \'' + pubUrl + '\', \'' + item.title + '\')" style="flex:1; padding:8px; background:#1a5c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">✅ 批准加入视频区</button>' +
      '<button onclick="rejectPendingItem(\'' + item.id + '\', \'' + item.file_path + '\')" style="flex:1; padding:8px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">❌ 拒绝删除</button>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

// ===== 通用拒绝函数（照片/视频/文件共用） =====

function addVideoThumb(videoSrc, label) {
  var thumbs = document.getElementById("videoThumbs");
  if (!thumbs) return;
  var idx = thumbs.children.length;
  var div = document.createElement("div");
  div.className = "video-thumb";
  div.innerHTML = '<div class="video-thumb-icon">▶</div><div class="video-thumb-label">' + label + '</div>';
  div.onclick = (function(i) { return function() { switchVideo(i, div); }; })(idx);
  thumbs.appendChild(div);
  if (window.videoList) {
    window.videoList.push({ src: videoSrc, title: label });
  }
}

// ===== 管理员：审核待审核PPT/文件 =====
async function loadPendingPpts() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingPptsList");
  var badge = document.getElementById("pendingPptBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "pending")
    .eq("file_type", "document")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data;
  if (badge) badge.textContent = items.length > 0 ? items.length + " 条" : "";

  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无待审核文件</span>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = item.file_path.startsWith("github:") ? item.file_path.replace("github:","") : supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    var ext = item.file_name.split(".").pop().toUpperCase();
    var icon = ext === "PDF" ? "📄" : (["PPT","PPTX"].includes(ext) ? "📊" : "📁");
    html += '<div style="border:1px solid #a0c4e8; border-radius:8px; padding:12px; margin-bottom:12px; background:#f0f6ff;">' +
      '<div style="display:flex; gap:12px; align-items:flex-start;">' +
      '<div style="width:100px; height:80px; background:#e8f0fe; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:36px; flex-shrink:0;">' + icon + '</div>' +
      '<div style="flex:1;">' +
      '<div style="font-weight:bold; font-size:14px; color:#333; margin-bottom:4px;">📌 ' + item.title + '</div>' +
      '<div style="font-size:12px; color:#888;">上传者：' + (item.uploaded_by || '匿名') + '</div>' +
      '<div style="font-size:12px; color:#888;">时间：' + date + '</div>' +
      '<div style="font-size:12px; color:#888; word-break:break-all;">文件：' + item.file_name + ' (' + ext + ')</div>' +
      '<a href="' + pubUrl + '" target="_blank" style="font-size:12px; color:#003366;">🔗 预览/下载文件</a>' +
      '</div></div>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approvePpt(\'' + item.id + '\', \'' + pubUrl + '\', \'' + item.title + '\', \'' + item.file_name + '\')" style="flex:1; padding:8px; background:#003366; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">✅ 批准发布到PPT区</button>' +
      '<button onclick="rejectPendingItem(\'' + item.id + '\', \'' + item.file_path + '\')" style="flex:1; padding:8px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">❌ 拒绝删除</button>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

function addPptFileEntry(fileUrl, title, fileName) {
  var pptContent = document.getElementById("pptContent");
  if (!pptContent) return;
  var ext = fileName.split(".").pop().toUpperCase();
  var icon = ext === "PDF" ? "📄" : (["PPT","PPTX"].includes(ext) ? "📊" : "📁");
  var div = document.createElement("div");
  div.style.cssText = "border-top:1px solid #ddd; padding:12px 0; display:flex; align-items:center; gap:12px;";
  div.innerHTML = '<span style="font-size:24px;">' + icon + '</span>' +
    '<div style="flex:1;">' +
      '<div style="font-weight:bold; color:#003366; font-size:14px;">' + title + '</div>' +
      '<div style="font-size:12px; color:#888;">' + fileName + '</div>' +
    '</div>' +
    '<div style="display:flex; gap:8px;">' +
      '<a href="' + fileUrl + '" target="_blank" style="padding:6px 12px; background:#003366; color:#fff; border-radius:6px; font-size:13px; text-decoration:none;">下载</a>' +
      '<a href="' + fileUrl + '" target="_blank" style="padding:6px 12px; background:#eee; color:#333; border-radius:6px; font-size:13px; text-decoration:none;">查看</a>' +
    '</div>';
  pptContent.appendChild(div);
}

// ===== 有缘千里来相会功能 =====
var userPendingYuanfen = null;

function toggleYuanfenUpload() {
  var box = document.getElementById("yuanfenUploadBox");
  if (box) box.style.display = box.style.display === "none" ? "block" : "none";
}

function yuanfenFileDrop(e) {
  e.preventDefault();
  document.getElementById("yuanfenDropZone").style.background = "#eef3fa";
  if (e.dataTransfer.files.length) yuanfenFileSelected(e.dataTransfer.files);
}

function yuanfenFileSelected(files) {
  if (!files.length) return;
  var file = files[0];
  var ext = file.name.split(".").pop().toLowerCase();
  var allowed = ["pdf","jpg","jpeg","png","gif","doc","docx","ppt","pptx"];
  if (!allowed.includes(ext)) {
    alert("请选择支持的格式：PDF、图片、Word、PPT 等");
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    alert("文件不能超过 50MB");
    return;
  }
  userPendingYuanfen = file;
  var preview = document.getElementById("yuanfenFilePreview");
  if (preview) {
    document.getElementById("yuanfenPreviewNameText").textContent = file.name;
    var size = file.size > 1024*1024 ? (file.size/1024/1024).toFixed(1)+"MB" : (file.size/1024).toFixed(0)+"KB";
    document.getElementById("yuanfenPreviewSize").textContent = "文件大小：" + size;
    preview.style.display = "block";
  }
}

async function submitJingcaiFile() {
  var supabase = window._supabaseClient;
  var msg = document.getElementById("jingcaiUploadMsg");
  if (!supabase) { msg.textContent = "请先登录网站"; msg.style.color = "crimson"; return; }
  if (!userPendingJingcai) { msg.textContent = "请先选择文件"; msg.style.color = "crimson"; return; }
  var title = document.getElementById("jingcaiFileTitle").value.trim();
  if (!title) { msg.textContent = "请填写标题"; msg.style.color = "crimson"; return; }
  msg.textContent = "上传中，请稍候...";
  msg.style.color = "#2e5a2e";
  var ext = userPendingJingcai.name.split(".").pop().toLowerCase();
  var filePath = "pending_jingcai/" + Date.now() + "." + ext;
  var uploadResult = await supabase.storage.from("uploads").upload(filePath, userPendingJingcai, { upsert: true });
  if (uploadResult.error) { msg.textContent = "上传失败：" + uploadResult.error.message; msg.style.color = "crimson"; return; }
  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : "匿名";
  var dbResult = await supabase.from("pending_uploads").insert({
    file_path: filePath,
    file_name: userPendingJingcai.name,
    title: title,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "jingcai"
  }).select().single();
  if (dbResult.error) { msg.textContent = "提交失败：" + dbResult.error.message; msg.style.color = "crimson"; return; }

  var pendingId = dbResult.data.id;
  msg.textContent = "转存到GitHub中...";
  msg.style.color = "#c07000";

  try {
    await uploadToGitHubViaEdge(pendingId, "jingcai");
    msg.textContent = "✅ 上传成功！已保存到GitHub，等待管理员审核。";
    msg.style.color = "green";
  } catch (e) {
    console.error("[精彩分享 GitHub转存失败]", e.message);
    msg.textContent = "⚠️ 已提交审核，等待管理员审核（GitHub转存失败：" + e.message + "）";
    msg.style.color = "#c07000";
  }

  sendResendNotification('精彩分享', title, uploadedBy);
  userPendingJingcai = null;
  document.getElementById("jingcaiFileTitle").value = "";
  document.getElementById("jingcaiFilePreview").style.display = "none";
  document.getElementById("jingcaiFileInput").value = "";
}

var userPendingJingcai = null;

function jingcaiFileSelected(files) {
  if (!files || !files[0]) return;
  userPendingJingcai = files[0];
  var preview = document.getElementById("jingcaiFilePreview");
  document.getElementById("jingcaiPreviewNameText").textContent = files[0].name;
  document.getElementById("jingcaiPreviewSize").textContent = (files[0].size / 1024 / 1024).toFixed(2) + " MB";
  preview.style.display = "flex";
}

function jingcaiFileDrop(e) {
  e.preventDefault();
  document.getElementById("jingcaiDropZone").classList.remove("jingcai-dropzone-active");
  jingcaiFileSelected(e.dataTransfer.files);
}

function toggleJingcaiUpload() {
  var box = document.getElementById("jingcaiUploadBox");
  box.style.display = box.style.display === "none" ? "block" : "none";
}

async function loadJingcaiItems() {
  var supabase = window._supabaseClient;
  var container = document.getElementById("jingcai-items");
  if (!container) return;
  if (!supabase) {
    container.innerHTML = '<div class="jingcai-empty"><div class="jingcai-empty-icon">&#128274;</div><div>请登录后查看</div></div>';
    return;
  }
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "jingcai")
    .order("uploaded_at", { ascending: false });
  if (result.error || !result.data || !result.data.length) {
    container.innerHTML = '<div class="jingcai-empty"><div class="jingcai-empty-icon">&#10024;</div><div>暂无内容，快来第一个分享吧</div></div>';
    return;
  }
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '<div class="jingcai-grid">';
  result.data.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var ext = item.file_name.split(".").pop().toUpperCase();
    var isImg = ["JPG","JPEG","PNG","GIF"].includes(ext);
    var date = new Date(item.uploaded_at).toLocaleDateString("zh-CN", { year:'numeric', month:'long', day:'numeric' });
    var uploader = item.uploaded_by ? item.uploaded_by.split('@')[0] : '匿名';
    var icon = ext === 'PDF' ? '&#128196;' : (['PPT','PPTX'].includes(ext) ? '&#128202;' : ['DOC','DOCX'].includes(ext) ? '&#128221;' : '&#128196;');
    html += '<div class="jingcai-card">';
    if (isImg) {
      html += '<img src="' + pubUrl + '" class="jingcai-card-thumb" onclick="openOverlay(\'' + pubUrl + '\', \'' + item.title + '\')" alt="' + item.title + '">';
    } else {
      html += '<div class="jingcai-card-icon">' + icon + '</div>';
    }
    html += '<div class="jingcai-card-body">' +
      '<div class="jingcai-card-title">' + item.title + '</div>' +
      '<div class="jingcai-card-meta">' + uploader + ' · ' + date + '</div>' +
      '<a href="' + pubUrl + '" target="_blank" class="jingcai-card-btn">查看 →</a>' +
      '</div></div>';
  });
  html += '</div>';
  container.innerHTML = html;
}

// ===== 已发布精彩管理 =====
async function loadApprovedJingcaiManager() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("approvedJingcaiManager");
  var badge = document.getElementById("approvedJingcaiBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "approved").eq("file_type", "jingcai")
    .order("uploaded_at", { ascending: false });
  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }
  var items = result.data || [];
  if (badge) badge.textContent = items.length + " 条";
  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无已发布内容</span>';
    return;
  }
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var ext = (item.file_name || '').split('.').pop().toUpperCase();
    var isImg = ['JPG','JPEG','PNG','GIF','WEBP'].includes(ext);
    var date = item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString('zh-CN') : '';
    html += '<div class="admin-mgr-card" data-id="' + item.id + '" data-path="' + encodeURIComponent(item.file_path) + '" data-title="' + encodeURIComponent(item.title||'') + '" data-type="jingcai">';
    if (isImg) {
      html += '<img class="admin-mgr-thumb" src="' + pubUrl + '" onclick="openOverlay(this.src,\'\')">';
    } else {
      html += '<div class="admin-mgr-thumb" style="background:#eef3fa;display:flex;align-items:center;justify-content:center;font-size:32px;">📄</div>';
    }
    html += '<div class="admin-mgr-body">' +
      '<div class="admin-mgr-title">' + (item.title||'未命名') + '</div>' +
      '<div class="admin-mgr-meta">上传者：' + (item.uploaded_by||'匿名') + ' · ' + date + '</div>' +
      '<div class="admin-mgr-actions">' +
        '<button class="admin-mgr-edit-btn" onclick="adminEditTitle(this)">✏️ 改标题</button>' +
        '<button class="admin-mgr-del-btn" onclick="deleteApprovedJingcaiItem(\' + item.id + \', \' + item.file_path + \', this)">🗑 删除</button>' +
      '</div>' +
    '</div></div>';
  });
  container.innerHTML = html || '<span style="color:#aaa;">暂无内容</span>';
}

async function deleteApprovedJingcaiItem(id, filePath, btn) {
  if (!confirm('确认永久删除这条精彩内容？将同时从数据库和存储中删除，不可恢复。')) return;
  if (btn) { btn.disabled = true; btn.textContent = '删除中...'; }
  var supabase = window._supabaseClient;
  await supabase.from('pending_uploads').delete().eq('id', id);
  await supabase.storage.from('uploads').remove([filePath]);
  loadApprovedJingcaiManager();
  loadJingcaiItems();
}

async function deleteAllApprovedJingcai() {
  if (!confirm('确认清空全部已发布精彩内容？此操作不可恢复。')) return;
  var supabase = window._supabaseClient;
  var result = await supabase.from('pending_uploads').select('id,file_path')
    .eq('status','approved').eq('file_type','jingcai');
  if (result.error || !result.data.length) { alert('暂无内容可清空'); return; }
  var ids = result.data.map(function(i){return i.id;});
  var paths = result.data.map(function(i){return i.file_path;});
  await supabase.from('pending_uploads').delete().in('id', ids);
  await supabase.storage.from('uploads').remove(paths);
  loadApprovedJingcaiManager();
  loadJingcaiItems();
  alert('✅ 已清空全部精彩内容（共 ' + ids.length + ' 条）');
}

// 管理员：加载待审核精彩内容
async function loadPendingJingcai() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingJingcaiList");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';
  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "pending").eq("file_type", "jingcai")
    .order("uploaded_at", { ascending: false });
  if (result.error) { container.innerHTML = '<span style="color:crimson;">加载失败</span>'; return; }
  var items = result.data;
  if (!items.length) { container.innerHTML = '<span style="color:#aaa;">暂无待审核内容</span>'; return; }
  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    html += '<div style="border:1px solid #c8ddc0; border-radius:8px; padding:12px; margin-bottom:12px; background:#f7fbf5;">' +
      '<div style="font-weight:bold; color:#2e5a2e; margin-bottom:4px;">&#128204; ' + item.title + '</div>' +
      '<div style="font-size:12px; color:#888; margin-bottom:4px;">上传者：' + (item.uploaded_by||'匿名') + ' · ' + date + '</div>' +
      '<a href="' + pubUrl + '" target="_blank" style="font-size:12px; color:#4a7a4a;">预览/下载</a>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approveJingcai(\'' + item.id + '\')" style="flex:1; padding:8px; background:#4a7a4a; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">批准发布</button>' +
      '<button onclick="rejectPendingItem(\'' + item.id + '\', \'' + item.file_path + '\')" style="flex:1; padding:8px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">拒绝删除</button>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function approveJingcai(id) {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  await supabase.from("pending_uploads").update({ status: "approved" }).eq("id", id);
  loadPendingJingcai();
  loadJingcaiItems();
}

// ===== 管理员：加载待审核Q&A问题 =====
async function loadPendingQA() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingQAList");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var result = await supabase.from("pending_uploads").select("*")
    .eq("status", "pending")
    .eq("file_type", "qa_question")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data;
  var badge = document.getElementById("pendingQABadge");
  if (badge) badge.textContent = items.length > 0 ? items.length + "条" : "";

  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无待审核问题</span>';
    return;
  }

  var html = '';
  items.forEach(function(item) {
    var metadata = {};
    try {
      metadata = JSON.parse(item.metadata || "{}");
    } catch(e) {}

    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    var question = item.title || item.file_name;
    var context = metadata.context || "（无补充说明）";
    var submitterName = metadata.submitter_name || "未知";

    html += '<div style="border:1px solid #b3d9ff; border-radius:8px; padding:14px; margin-bottom:12px; background:#f0f7ff;">' +
      '<div style="font-weight:bold; color:#003366; margin-bottom:6px; font-size:14px;">❓ ' + question + '</div>' +
      '<div style="font-size:12px; color:#555; margin-bottom:8px; padding:8px; background:#e8f1ff; border-radius:4px; border-left:3px solid #003366;">' +
      '<strong>补充说明：</strong>' + context + '</div>' +
      '<div style="font-size:12px; color:#888; margin-bottom:10px;">' +
      '提问者：<strong>' + submitterName + '</strong> · ' + date + '<br>' +
      '邮箱：' + (item.uploaded_by || '匿名') + '</div>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approveQA(\'' + item.id + '\')" style="flex:1; padding:10px; background:#003366; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">✅ 批准发布</button>' +
      '<button onclick="rejectQA(\'' + item.id + '\')" style="flex:1; padding:10px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">❌ 拒绝删除</button>' +
      '</div></div>';
  });

  container.innerHTML = html;
}

async function approveQA(id) {
  if (!confirm("批准此问题并添加到Q&A部分？")) return;
  var supabase = window._supabaseClient;
  if (!supabase) return;

  var result = await supabase.from("pending_uploads").update({ status: "approved" }).eq("id", id);

  if (result.error) {
    alert("操作失败：" + result.error.message);
  } else {
    alert("✅ 问题已批准发布！");
    loadPendingQA();
  }
}

async function rejectQA(id) {
  if (!confirm("确认拒绝此问题？")) return;
  var supabase = window._supabaseClient;
  if (!supabase) return;

  var result = await supabase.from("pending_uploads").update({ status: "rejected" }).eq("id", id);

  if (result.error) {
    alert("操作失败：" + result.error.message);
  } else {
    alert("已拒绝此问题。");
    loadPendingQA();
  }
}

// 加载时触发
document.addEventListener("supabaseReady", function() {
  loadJingcaiItems();
});


async function submitYuanfenFile() {
  var supabase = window._supabaseClient;
  var msg = document.getElementById("yuanfenUploadMsg");
  if (!supabase) { msg.textContent = "请先登录网站"; msg.style.color = "crimson"; return; }
  if (!userPendingYuanfen) { msg.textContent = "请先选择文件"; msg.style.color = "crimson"; return; }

  var title = document.getElementById("yuanfenFileTitle").value.trim();
  if (!title) { msg.textContent = "请填写标题/说明"; msg.style.color = "crimson"; return; }

  msg.textContent = "上传中，请稍候...";
  msg.style.color = "#003366";

  var ext = userPendingYuanfen.name.split(".").pop().toLowerCase();
  var filePath = "pending_yuanfen/" + Date.now() + "." + ext;
  var uploadResult = await supabase.storage.from("uploads").upload(filePath, userPendingYuanfen, { upsert: true });

  if (uploadResult.error) {
    msg.textContent = "上传失败：" + uploadResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var { data: { user } } = await supabase.auth.getUser();
  var uploadedBy = user && user.email ? user.email : "匿名";

  var dbResult = await supabase.from("pending_uploads").insert({
    file_path: filePath,
    file_name: userPendingYuanfen.name,
    title: title,
    uploaded_by: uploadedBy,
    status: "pending",
    file_type: "yuanfen"
  }).select().single();

  if (dbResult.error) {
    msg.textContent = "提交失败：" + dbResult.error.message;
    msg.style.color = "crimson";
    return;
  }

  var pendingId = dbResult.data.id;
  msg.textContent = "转存到GitHub中...";
  msg.style.color = "#c07000";

  try {
    await uploadToGitHubViaEdge(pendingId, "yuanfen");
    msg.textContent = "✅ 上传成功！已保存到GitHub，等待管理员审核。";
    msg.style.color = "green";
  } catch (e) {
    console.error("[有缘启示 GitHub转存失败]", e.message);
    msg.textContent = "⚠️ 已提交审核，等待管理员审核（GitHub转存失败：" + e.message + "）";
    msg.style.color = "#c07000";
  }

  sendResendNotification('有缘启示', title, uploadedBy);
  userPendingYuanfen = null;
  document.getElementById("yuanfenFileTitle").value = "";
  document.getElementById("yuanfenFilePreview").style.display = "none";
  document.getElementById("yuanfenFileInput").value = "";
}

// 加载已发布的有缘启示（供所有用户查看）
async function loadYuanfenItems() {
  var supabase = window._supabaseClient;
  var container = document.getElementById("yuanfen-items");
  if (!container) return;
  if (!supabase) {
    container.innerHTML = '<div class="yuanfen-empty"><div class="yuanfen-empty-icon">🔒</div><div class="yuanfen-empty-text">请登录后查看</div></div>';
    return;
  }

  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "approved")
    .eq("file_type", "yuanfen")
    .order("uploaded_at", { ascending: false });

  if (result.error || !result.data || !result.data.length) {
    container.innerHTML = '<div class="yuanfen-empty"><div class="yuanfen-empty-icon">💌</div><div class="yuanfen-empty-text">暂无有缘启示<br>快来发布第一条吧～</div></div>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  result.data.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var ext = item.file_name.split(".").pop().toUpperCase();
    var isImg = ["JPG","JPEG","PNG","GIF"].includes(ext);
    var date = new Date(item.uploaded_at).toLocaleDateString("zh-CN", { year:'numeric', month:'long', day:'numeric' });
    var uploader = item.uploaded_by ? item.uploaded_by.split('@')[0] : '匿名';

    html += '<div class="yuanfen-card">';
    if (isImg) {
      html += '<img src="' + pubUrl + '" class="yuanfen-card-thumb" onclick="openOverlay(\'' + pubUrl + '\', \'' + item.title + '\')" alt="' + item.title + '">';
    } else {
      var icon = ext === 'PDF' ? '📄' : (['PPT','PPTX'].includes(ext) ? '📊' : ['DOC','DOCX'].includes(ext) ? '📝' : '💌');
      html += '<div class="yuanfen-card-icon">' + icon + '</div>';
    }
    html += '<div class="yuanfen-card-body">' +
      '<div class="yuanfen-card-title">' + item.title + '</div>' +
      '<div class="yuanfen-card-meta">' + uploader + ' · ' + date + '</div>' +
      '<a href="' + pubUrl + '" target="_blank" class="yuanfen-card-btn">查看 →</a>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

// 管理员：加载待审核有缘启示
async function loadPendingYuanfen() {
  var supabase = window._supabaseClient;
  if (!supabase) return;
  var container = document.getElementById("pendingYuanfenList");
  var badge = document.getElementById("pendingYuanfenBadge");
  if (!container) return;
  container.innerHTML = '<span style="color:#aaa;">加载中...</span>';

  var result = await supabase
    .from("pending_uploads")
    .select("*")
    .eq("status", "pending")
    .eq("file_type", "yuanfen")
    .order("uploaded_at", { ascending: false });

  if (result.error) {
    container.innerHTML = '<span style="color:crimson;">加载失败：' + result.error.message + '</span>';
    return;
  }

  var items = result.data;
  if (badge) badge.textContent = items.length > 0 ? items.length + " 条" : "";

  if (!items.length) {
    container.innerHTML = '<span style="color:#aaa;">暂无待审核有缘启示</span>';
    return;
  }

  var supabaseUrl = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  var html = '';
  items.forEach(function(item) {
    var pubUrl = supabaseUrl + "/storage/v1/object/public/uploads/" + item.file_path;
    var date = new Date(item.uploaded_at).toLocaleString("zh-CN");
    var ext = item.file_name.split(".").pop().toUpperCase();
    var isImg = ["JPG","JPEG","PNG","GIF"].includes(ext);
    html += '<div style="border:1px solid #e8c8e8; border-radius:8px; padding:12px; margin-bottom:12px; background:#fff9fe;">' +
      '<div style="display:flex; gap:12px; align-items:flex-start;">';
    if (isImg) {
      html += '<img src="' + pubUrl + '" style="width:100px; height:80px; object-fit:cover; border-radius:6px; border:1px solid #ddd; cursor:pointer;" onclick="openOverlay(\'' + pubUrl + '\', \'' + item.title + '\')">';
    } else {
      html += '<div style="width:100px; height:80px; background:#f5e8ff; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:36px; flex-shrink:0;">💌</div>';
    }
    html += '<div style="flex:1;">' +
      '<div style="font-weight:bold; font-size:14px; color:#7a0060; margin-bottom:4px;">📌 ' + item.title + '</div>' +
      '<div style="font-size:12px; color:#888;">上传者：' + (item.uploaded_by || '匿名') + '</div>' +
      '<div style="font-size:12px; color:#888;">时间：' + date + '</div>' +
      '<div style="font-size:12px; color:#888; word-break:break-all;">文件：' + item.file_name + '</div>' +
      '<a href="' + pubUrl + '" target="_blank" style="font-size:12px; color:#7a0060;">🔗 预览/下载</a>' +
      '</div></div>' +
      '<div style="margin-top:10px; display:flex; gap:8px;">' +
      '<button onclick="approveYuanfen(\'' + item.id + '\')" style="flex:1; padding:8px; background:#7a0060; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">✅ 批准发布</button>' +
      '<button onclick="rejectPendingItem(\'' + item.id + '\', \'' + item.file_path + '\')" style="flex:1; padding:8px; background:#c00; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px;">❌ 拒绝删除</button>' +
      '</div></div>';
  });
  container.innerHTML = html;
}

async function approveYuanfen(id) {
  if (!confirm("批准此有缘启示并发布？")) return;
  var supabase = window._supabaseClient;
  var result = await supabase
    .from("pending_uploads")
    .update({ status: "approved" })
    .eq("id", id);

  if (result.error) {
    alert("操作失败：" + result.error.message);
  } else {
    alert("已发布！");
    loadPendingYuanfen();
    loadYuanfenItems();
  }
}

async function rejectPendingItem(id, filePath) {
  if (!confirm("确认拒绝并删除此文件？")) return;
  var supabase = window._supabaseClient;
  var actualPath = filePath.startsWith("github:") ? null : filePath;
  await supabase.from("pending_uploads").update({ status: "rejected" }).eq("id", id);
  if (actualPath) await supabase.storage.from("uploads").remove([actualPath]);
  alert("已拒绝并删除。");
  loadPendingUploads();
  loadPendingVideos();
  loadPendingPpts();
}
