(function () {

  const SUPABASE_URL      = 'https://ritglkwqpwlcjwemhfqd.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpdGdsa3dxcHdsY2p3ZW1oZnFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3MzEyMTQsImV4cCI6MjA4NzMwNzIxNH0.TqjETAEGcWTd2CbvkMnmfm6bKHLtZHjXbsy3dtPuEB8';
  const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  window._supabaseClient = client; // 供 script.js / admin.js 共用

  // ─── 修复 Auth session missing：监听 PASSWORD_RECOVERY 事件 ───────────────
  // 当用户点击邮件里的重置密码链接，Supabase 会触发 PASSWORD_RECOVERY 事件
  // 此时必须先用 onAuthStateChange 拿到 session，再跳转到重置密码页
  client.auth.onAuthStateChange(function(event, session) {
    if (event === 'PASSWORD_RECOVERY') {
      // session 已建立，安全跳转到重置密码页
      window.location.href = '/reset-password.html';
    }
  });
  // ─────────────────────────────────────────────────────────────────────────

  function showLogin() {
    document.getElementById("protected-area").innerHTML = `
      <div style="text-align:center;margin-top:0;padding:80px 20px 40px 20px;background-image:url(https://dukeparents.org/chapel.jpg);background-size:cover;background-position:center;background-repeat:no-repeat;position:relative;min-height:320px;display:flex;align-items:center;justify-content:center;">
      <div style="position:absolute;inset:0;background:rgba(255,255,255,0.80);"></div>
      <div style="position:relative;z-index:1;width:100%;">
      <h2 style="font-family: SIMLI, serif;">蓝魔港湾</h2>
        <h2 style="font-family: SIMLI, serif;">扯谈<span class="gothic">𝔇𝔲𝔨𝔢</span>群社区</h2>
        <a href="login.html" style="display:inline-block;padding:12px 32px;background:#003366;color:#fff;border-radius:8px;text-decoration:none;font-size:16px;">登录</a>
      </div>
      </div>
    `;
  }

  function showContent(user) {
    if (typeof window.incrementAndShowPV === "function") window.incrementAndShowPV();
    const template = document.getElementById("real-content");
    const clone = template.content.cloneNode(true);
    const main = document.getElementById("protected-area");
    main.innerHTML = "";
    main.appendChild(clone);

    // === 退出登录按钮 ===
    const oldBtn = document.getElementById("logoutBtnFixed");
    if (oldBtn) oldBtn.remove();
    const logoutBtn = document.createElement("button");
    logoutBtn.id = "logoutBtnFixed";
    logoutBtn.innerText = "退出登录";
    logoutBtn.className = "logout-btn-fixed";
    logoutBtn.onclick = async function () {
      await client.auth.signOut();
      location.reload();
    };
    document.body.appendChild(logoutBtn);

    // === 动态注入官方链接（绕过Cloudflare链接保护）===
    (function() {
      var officialLinks = [
        { url: "https://go.gallagherstudent.com/Universities/Duke%20University/Home", text: "\uD83D\uDD17 Gallagher\u5b66\u751f\u95E8\u6237(\u8C41\u514D/\u6CE8\u518C\u7533\u8BF7)" },
        { url: "https://students.duke.edu/wellness/studenthealth/insurance/", text: "\uD83D\uDD17 Duke\u533B\u7597\u4FDD\u9669\u603B\u89C8(Duke Student Affairs)" },
        { url: "https://students.duke.edu/wellness/studenthealth/insurance/enrolling-in-or-waiving-smip/", text: "\uD83D\uDD17 \u6CE8\u518C\u6216\u8C41\u514DSMIP\u64CD\u4F5C\u6307\u5357" },
        { url: "https://students.duke.edu/wellness/studenthealth/insurance/faqs-contact-us/", text: "\uD83D\uDD17 \u4FDD\u9669FAQ\u4E0E\u8054\u7CFB\u65B9\u5F0F" },
        { url: "https://financialaid.duke.edu/making-most-your-aid/health-insurance/", text: "\uD83D\uDD17 Karsh\u52A9\u5B66\u91D1\u529E\u516C\u5BA4\uFF1A\u4FDD\u9669\u8D39\u7528\u8BF4\u660E" },
        { url: "https://go.gallagherstudent.com/-/media/files/gsh/universities/duke-university/25-26-plan/20252026-duke-university-smip-faq.pdf", text: "\uD83D\uDCC4 2025-2026 SMIP FAQ\u5B8C\u6574PDF(Gallagher)" },
        { url: "https://www.bluecrossnc.com/content/dam/bcbsnc/pdf/members/student-blue/duke-university/duke-brochure-25-26.pdf", text: "\uD83D\uDCC4 Student Blue\u4FDD\u9669\u624B\u518CPDF" }
      ];

      function injectLinks(container) {
        container.innerHTML = "";
        officialLinks.forEach(function(item) {
          var a = document.createElement("a");
          a.setAttribute("href", item.url);
          a.setAttribute("target", "_blank");
          a.setAttribute("rel", "noopener noreferrer");
          a.appendChild(document.createTextNode(item.text));
          container.appendChild(a);
        });
      }

      var byId = main.querySelector("#insurance-official-links");
      if (byId) { injectLinks(byId); return; }

      var titles = main.querySelectorAll(".section-title");
      for (var i = 0; i < titles.length; i++) {
        if (titles[i].textContent.trim() === "\u5B98\u65B9\u94FE\u63A5") {
          var container = document.createElement("div");
          container.id = "insurance-official-links";
          titles[i].parentNode.insertBefore(container, titles[i].nextSibling);
          injectLinks(container);
          return;
        }
      }
    })();

    // === 登录后还原图片/视频/PDF的真实路径 ===
    main.querySelectorAll("img[data-src]").forEach(function(el) {
      el.src = el.getAttribute("data-src");
    });
    main.querySelectorAll("source[data-src]").forEach(function(el) {
      el.src = el.getAttribute("data-src");
      var video = el.closest("video");
      if (video) video.load();
    });
    main.querySelectorAll("iframe[data-src]").forEach(function(el) {
      el.src = el.getAttribute("data-src");
    });

    // === 图片放大 ===
    main.querySelectorAll("img.thumb").forEach(function(img) {
      img.onclick = function() { openOverlay(img.src, img.alt); };
    });

    // === 轮播相册初始化 ===
    var _slideshowState = { current: 0, total: 0, autoTimer: null, inited: false };

    window.initMainSlideshow = function() {
      var slides = main.querySelectorAll("#slideshowTrack .slide");
      var dotsContainer = main.querySelector("#slideDots");
      var counter = main.querySelector("#slideCounter");
      if (!slides.length) return;

      clearInterval(_slideshowState.autoTimer);
      _slideshowState.current = 0;
      _slideshowState.total = slides.length;

      slides.forEach(function(s, i) { s.classList.toggle("active", i === 0); });

      dotsContainer.innerHTML = "";
      slides.forEach(function(_, i) {
        var dot = document.createElement("span");
        dot.className = "slide-dot" + (i === 0 ? " active" : "");
        dot.onclick = function() { goTo(i); resetAuto(); };
        dotsContainer.appendChild(dot);
      });

      counter.textContent = "1 / " + slides.length;

      function goTo(n) {
        var s = main.querySelectorAll("#slideshowTrack .slide");
        var d = dotsContainer.children;
        if (!s.length) return;
        var total = s.length;
        s[_slideshowState.current] && s[_slideshowState.current].classList.remove("active");
        d[_slideshowState.current] && d[_slideshowState.current].classList.remove("active");
        _slideshowState.current = (n + total) % total;
        s[_slideshowState.current] && s[_slideshowState.current].classList.add("active");
        d[_slideshowState.current] && d[_slideshowState.current].classList.add("active");
        counter.textContent = (_slideshowState.current + 1) + " / " + total;
      }

      main.querySelector(".slide-prev").onclick = function() { goTo(_slideshowState.current - 1); resetAuto(); };
      main.querySelector(".slide-next").onclick = function() { goTo(_slideshowState.current + 1); resetAuto(); };

      function startAuto() {
        _slideshowState.autoTimer = setInterval(function() { goTo(_slideshowState.current + 1); }, 4000);
      }
      function resetAuto() {
        clearInterval(_slideshowState.autoTimer);
        startAuto();
      }
      startAuto();

      var touchStartX = 0;
      var trackEl = main.querySelector(".slideshow-container");
      if (!_slideshowState.inited) {
        trackEl.addEventListener("touchstart", function(e) {
          touchStartX = e.touches[0].clientX;
        }, { passive: true });
        trackEl.addEventListener("touchend", function(e) {
          var diff = touchStartX - e.changedTouches[0].clientX;
          if (Math.abs(diff) > 40) { goTo(_slideshowState.current + (diff > 0 ? 1 : -1)); resetAuto(); }
        }, { passive: true });
        _slideshowState.inited = true;
      }
    };

    // === 大家拍切换 ===
    window.videoList = [];

    window.switchVideo = function(index, thumbEl) {
      var mainVideo = main.querySelector("#mainVideo");
      var titleEl   = main.querySelector("#videoTitle");
      var thumbs    = main.querySelectorAll(".video-thumb");
      if (!mainVideo || !window.videoList[index]) return;
      mainVideo.pause();
      mainVideo.querySelector("source").src = window.videoList[index].src;
      mainVideo.load();
      if (titleEl) titleEl.textContent = "🎬 " + window.videoList[index].label;
      thumbs.forEach(function(t) { t.classList.remove("active"); });
      if (thumbEl) thumbEl.classList.add("active");
    };

    // === 手风琴折叠 ===
    window.toggleAccordion = function(btn) {
      var body = btn.nextElementSibling;
      var arrow = btn.querySelector(".accordion-arrow");
      var isOpen = body.classList.contains("open");
      body.classList.toggle("open", !isOpen);
      arrow.textContent = isOpen ? "▸" : "▾";
      btn.classList.toggle("active", !isOpen);
    };

    window.toggleSubAccordion = function(btn) {
      var body = btn.nextElementSibling;
      var arrow = btn.querySelector(".sub-accordion-arrow");
      var isOpen = body.classList.contains("sub-open");
      body.classList.toggle("sub-open", !isOpen);
      arrow.textContent = isOpen ? "▸" : "▾";
      btn.classList.toggle("sub-active", !isOpen);
    };

    // === PPT 展开/收起 ===
    const pptToggle = main.querySelector("#pptToggle");
    const pptContent = main.querySelector("#pptContent");
    if (pptToggle && pptContent) {
      pptToggle.addEventListener("click", function() {
        const isOpen = pptContent.style.display === "block";
        pptContent.style.display = isOpen ? "none" : "block";
        pptToggle.textContent = isOpen ? "展开" : "收起";
        pptToggle.setAttribute("aria-expanded", String(!isOpen));
      });
    }

    // === 搜索 ===
    const searchInput = main.querySelector("#searchInput");
    if (searchInput) {
      searchInput.addEventListener("input", function() {
        const keyword = this.value.trim().toLowerCase();
        const items = main.querySelectorAll(".link-list a, .link-list li");
        let firstMatch = null;
        items.forEach(function(el) {
          const text = el.textContent.toLowerCase();
          const match = text.includes(keyword);
          el.style.display = match ? "" : "none";
          if (match && !firstMatch && keyword !== "") firstMatch = el;
        });
        if (firstMatch) firstMatch.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }

    loadYuanfenItems();
    loadJingcaiItems();
    loadAdminVideoGallery();
    loadVideoGallery();
    loadAlbumPhotosToSlideshow();
    loadApprovedAdminPhotos();
  }

  async function checkLoginStatus() {
    const { data: { session } } = await client.auth.getSession();
    if (session) {
      const { data: profile } = await client
        .from('profiles')
        .select('has_set_password')
        .eq('id', session.user.id)
        .single();

      if (profile && !profile.has_set_password) {
        window.location.href = '/set-password.html';
        return;
      }

      showContent(session.user);
    } else {
      showLogin();
    }
  }

  checkLoginStatus();

})();
