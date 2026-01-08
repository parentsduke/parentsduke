/* ========== 图片放大 ========== */
const thumbs = document.querySelectorAll('.thumb');
const imgOverlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

thumbs.forEach(img => {
    img.addEventListener('click', () => {
        overlayImg.src = img.src;
        imgOverlay.classList.add('show');
    });
});

imgOverlay.addEventListener('click', () => {
    imgOverlay.classList.remove('show');
    overlayImg.src = '';
});

/* ========== 视频放大 ========== */
const videoWrappers = document.querySelectorAll('.video-wrapper');
const videoOverlay = document.getElementById('video-overlay');
const overlayVideo = document.getElementById('overlay-video');

videoWrappers.forEach(wrapper => {
    const video = wrapper.querySelector('video');

    wrapper.addEventListener('click', () => {
        // 获取视频 src
        const src = video.currentSrc || video.querySelector('source')?.src || '';
        if (!src) return;

        overlayVideo.pause();
        overlayVideo.src = '';
        overlayVideo.src = src;
        videoOverlay.classList.add('show');
        overlayVideo.play();
    });
});

// 点击遮罩关闭
videoOverlay.addEventListener('click', () => {
    overlayVideo.pause();
    overlayVideo.src = '';
    videoOverlay.classList.remove('show');
});

// 阻止点击视频本身关闭 overlay
overlayVideo.addEventListener('click', e => e.stopPropagation());
