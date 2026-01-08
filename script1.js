/* ========== 图片单击放大 ========== */
const thumbs = document.querySelectorAll('.thumb');
const imgOverlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

thumbs.forEach(img => {
  img.addEventListener('click', () => {
    overlayImg.src = img.src;
    imgOverlay.style.display = 'flex';
  });
});

imgOverlay.addEventListener('click', () => {
  imgOverlay.style.display = 'none';
});


/* ========== 视频单击放大（重点） ========== */


const videoWrappers = document.querySelectorAll('.video-wrapper');
const videoOverlay = document.getElementById('video-overlay');
const overlayVideo = document.getElementById('overlay-video');
const src = video.currentSrc || video.querySelector('source')?.src || '';
overlayVideo.src = src;

videoWrappers.forEach(wrapper => {
  const video = wrapper.querySelector('video');

  wrapper.addEventListener('click', () => {
    overlayVideo.src = video.currentSrc || video.src; // 确保能取到视频路径
    videoOverlay.style.display = 'flex';
    overlayVideo.play();
  });
});

// 点击遮罩层关闭
videoOverlay.addEventListener('click', () => {
  overlayVideo.pause();
  overlayVideo.src = '';
  videoOverlay.style.display = 'none';
});

// 阻止点击视频本身关闭 overlay
overlayVideo.addEventListener('click', e => e.stopPropagation());
