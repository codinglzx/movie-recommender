/**
 * 电影推荐系统 - 前端交互逻辑
 */

// ========== Toast 通知系统 ==========
class Toast {
    static container = null;

    static init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    static show(message, type = 'info', duration = 4000) {
        this.init();
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 12 9 17 20 6"/></svg>',
            error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
            warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d4895a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 22h20L12 2z"/><line x1="12" y1="10" x2="12" y2="15"/><circle cx="12" cy="18.5" r="0.5" fill="#d4895a" stroke="none"/></svg>',
            info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c8a84e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="10.5" x2="12" y2="17"/><circle cx="12" cy="7.5" r="0.5" fill="#c8a84e" stroke="none"/></svg>'
        };

        const closeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close">${closeIcon}</button>
        `;

        this.container.appendChild(toast);

        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.hide(toast));

        if (duration > 0) {
            setTimeout(() => this.hide(toast), duration);
        }
    }

    static hide(toast) {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }

    static success(message) { this.show(message, 'success'); }
    static error(message) { this.show(message, 'error'); }
    static warning(message) { this.show(message, 'warning'); }
    static info(message) { this.show(message, 'info'); }
}

// ========== 星级评分组件 ==========
class StarRating {
    constructor(container) {
        this.container = container;
        this.input = container.querySelector('.hidden-rating-input');
        this.stars = container.querySelectorAll('.star');
        this.ratingText = container.querySelector('.rating-text');
        this.selectedRating = 0;
        this.hoveredRating = 0;

        this.init();
    }

    init() {
        this.stars.forEach(star => {
            star.addEventListener('mouseenter', () => this.handleHover(star));
            star.addEventListener('mouseleave', () => this.handleLeave());
            star.addEventListener('click', () => this.handleClick(star));
        });
    }

    handleHover(star) {
        const rating = parseInt(star.dataset.value);
        this.hoveredRating = rating;
        this.updateStars(rating, false);
        this.updateRatingText(rating);
    }

    handleLeave() {
        this.hoveredRating = 0;
        this.updateStars(this.selectedRating, true);
        this.updateRatingText(this.selectedRating);
    }

    handleClick(star) {
        const rating = parseInt(star.dataset.value);
        this.selectedRating = rating;
        this.updateStars(rating, true);
        // 触发 pop 动画
        star.classList.remove('is-pop');
        // 强制重排重启动画
        void star.offsetWidth;
        star.classList.add('is-pop');
        if (this.input) {
            this.input.value = rating;
        }
        this.updateRatingText(rating);
        Toast.success(`你给出了 ${rating} 星评分！`);
    }

    updateStars(rating, isSelected) {
        this.stars.forEach(star => {
            const starRating = parseInt(star.dataset.value);
            star.classList.remove('hovered', 'selected');
            if (starRating <= rating) {
                star.classList.add(isSelected ? 'selected' : 'hovered');
            }
        });
    }

    updateRatingText(rating) {
        if (!this.ratingText) return;
        const texts = ['', '很差', '较差', '一般', '较好', '很好'];
        this.ratingText.textContent = rating ? texts[rating] : '点击星星评分';
    }

    getValue() {
        return this.selectedRating;
    }
}

// ========== 电影详情 Modal ==========
class MovieModal {
    constructor() {
        this.modal = null;
        this.modalBody = null;
        this.createModal();
    }

    createModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'modal-overlay';
        this.modal.innerHTML = `
            <div class="modal-content">
                <button class="modal-close">×</button>
                <div class="modal-header">
                    <div class="modal-poster"></div>
                    <div class="modal-info">
                        <h2></h2>
                        <div class="modal-meta"></div>
                        <div class="modal-genres"></div>
                        <div class="modal-rating">
                            <span class="stars"></span>
                            <span class="score"></span>
                        </div>
                        <div class="modal-overview"></div>
                    </div>
                </div>
                <div class="modal-body"></div>
            </div>
        `;
        document.body.appendChild(this.modal);
        this.modalBody = this.modal.querySelector('.modal-body');

        this.modal.querySelector('.modal-close').addEventListener('click', () => this.close());
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
        });
    }

    open(movie) {
        const content = this.modal.querySelector('.modal-content');

        // 标题
        content.querySelector('.modal-info h2').textContent = movie.title;

        // 海报
        const posterEl = content.querySelector('.modal-poster');
        posterEl.classList.remove('modal-poster-placeholder');
        posterEl.removeAttribute('data-genre');
        posterEl.innerHTML = '';
        if (movie.poster_path) {
            posterEl.style.background = '';
            posterEl.style.backgroundImage = `url('${movie.poster_path}')`;
        } else {
            posterEl.style.backgroundImage = 'none';
            posterEl.classList.add('modal-poster-placeholder');
            posterEl.dataset.genre = (movie.genres && movie.genres[0]) || '其他';
            posterEl.innerHTML = `<span>${escapeHTML((movie.title || '?')[0])}</span>`;
            posterEl.style.background = this.getGenreColor(movie.genres);
        }

        // 元信息
        const metaItems = [];
        const clockSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
        const fireSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px"><path d="M12 22c4.4 0 8-3.6 8-8 0-5-5.5-10-8-14-2.5 4-8 9-8 14 0 4.4 3.6 8 8 8z"/><path d="M12 19c-1.7 0-3-1.3-3-3 0-2 2-4.5 3-6 1 1.5 3 4 3 6 0 1.7-1.3 3-3 3z"/></svg>';
        if (movie.release_year) metaItems.push(`${clockSvg} ${escapeHTML(String(movie.release_year))}`);
        if (movie.popularity) metaItems.push(`${fireSvg} ${escapeHTML(String(Math.round(movie.popularity)))}`);
        content.querySelector('.modal-meta').innerHTML = metaItems.map(m => `<span>${m}</span>`).join('');

        // 类型标签
        const genresHtml = (movie.genres || []).map(g =>
            `<span class="modal-genre-tag">${escapeHTML(g)}</span>`
        ).join('');
        content.querySelector('.modal-genres').innerHTML = genresHtml;

        // 评分
        const ratingEl = content.querySelector('.modal-rating');
        if (movie.vote_average) {
            const fullStars = Math.floor(movie.vote_average / 2);
            const starsHtml = '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
            content.querySelector('.modal-rating .stars').textContent = starsHtml;
            content.querySelector('.modal-rating .score').textContent = movie.vote_average.toFixed(1);
            ratingEl.style.display = 'inline-flex';
        } else {
            ratingEl.style.display = 'none';
        }

        // 简介
        content.querySelector('.modal-overview').textContent = movie.overview || '暂无简介';

        // Modal Body - 评分区域
        if (window.__CURRENT_USER_ID__) {
            const userRating = this.getUserRating(movie.movie_id);
            this.modalBody.innerHTML = `
                <h3>我的评分</h3>
                <div class="modal-rating-form" data-movie-id="${movie.movie_id}">
                    <div class="star-rating-input" style="flex-direction: row; align-items: center; gap: 12px;">
                        <div class="stars">
                            ${[1,2,3,4,5].map(n => `<span class="star ${n <= userRating ? 'selected' : ''}" data-value="${n}" style="font-size: 28px; color: ${n <= userRating ? '#d4a843' : '#2a2a35'}; cursor: pointer;">★</span>`).join('')}
                        </div>
                        <span class="rating-text" style="color: #888; font-size: 13px;">${userRating ? '已评分' : '点击星星评分'}</span>
                    </div>
                    <input type="hidden" class="hidden-rating-input" value="${userRating}">
                </div>
            `;
            // 绑定评分事件
            this.modalBody.querySelectorAll('.star').forEach(star => {
                star.addEventListener('click', () => this.handleRating(movie.movie_id, parseInt(star.dataset.value)));
                star.addEventListener('mouseenter', () => {
                    const val = parseInt(star.dataset.value);
                    this.modalBody.querySelectorAll('.star').forEach((s, i) => {
                        s.style.color = i < val ? '#d4a843' : '#2a2a35';
                    });
                });
                star.addEventListener('mouseleave', () => {
                    const current = parseInt(this.modalBody.querySelector('.hidden-rating-input').value) || userRating;
                    this.modalBody.querySelectorAll('.star').forEach((s, i) => {
                        s.style.color = i < current ? '#d4a843' : '#2a2a35';
                    });
                });
            });
        } else {
            this.modalBody.innerHTML = '<p style="color: #888; text-align: center; padding: 10px;">登录后可评分</p>';
        }

        this.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    getUserRating(movieId) {
        return window.__USER_RATINGS__?.[movieId] || 0;
    }

    handleRating(movieId, rating) {
        if (!window.__CURRENT_USER_ID__) {
            Toast.warning('请先登录');
            return;
        }

        // 乐观更新：立刻把星星点亮，失败时回滚
        const previousRating = window.__USER_RATINGS__?.[movieId] || 0;
        if (!window.__USER_RATINGS__) window.__USER_RATINGS__ = {};
        window.__USER_RATINGS__[movieId] = rating;
        this.modalBody.querySelector('.hidden-rating-input').value = rating;
        this.modalBody.querySelector('.rating-text').textContent = '已评分';
        const stars = this.modalBody.querySelectorAll('.star');
        stars.forEach((s, i) => {
            s.style.color = i < rating ? '#d4a843' : '#2a2a35';
        });
        // pop 动画
        stars.forEach((s, i) => {
            if (i < rating) {
                s.classList.remove('is-pop');
                void s.offsetWidth;
                s.classList.add('is-pop');
            }
        });

        // 提交到后端（带 CSRF token）
        fetch('/api/rate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRF-Token': window.__CSRF_TOKEN__ || '',
            },
            body: `movie_id=${movieId}&rating=${rating}&_csrf_token=${encodeURIComponent(window.__CSRF_TOKEN__ || '')}`
        }).then(response => response.json())
          .then(data => {
            if (data.error) {
                // 失败回滚
                window.__USER_RATINGS__[movieId] = previousRating;
                this.modalBody.querySelector('.hidden-rating-input').value = previousRating;
                this.modalBody.querySelector('.rating-text').textContent = previousRating ? '已评分' : '点击星星评分';
                stars.forEach((s, i) => {
                    s.style.color = i < previousRating ? '#d4a843' : '#2a2a35';
                });
                Toast.error(data.error);
            } else {
                Toast.success(`评分成功：${rating} 星！`);
            }
          }).catch(() => {
            // 网络错误回滚
            window.__USER_RATINGS__[movieId] = previousRating;
            this.modalBody.querySelector('.hidden-rating-input').value = previousRating;
            this.modalBody.querySelector('.rating-text').textContent = previousRating ? '已评分' : '点击星星评分';
            stars.forEach((s, i) => {
                s.style.color = i < previousRating ? '#d4a843' : '#2a2a35';
            });
            Toast.error('评分失败，请重试');
          });
    }

    close() {
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    getGenreColor(genres) {
        return getGenreColor(genres);
    }
}

// ========== 电影搜索与筛选 ==========
class MovieSearch {
    constructor() {
        this.movies = [];
        this.filteredMovies = [];
        this.selectedGenre = null;
        this.selectedYear = null;
        this.searchQuery = '';
        this.debounceTimer = null;
    }

    init(movies) {
        this.movies = movies;
        this.filteredMovies = [...movies];
        this.updateCounter();
        this.bindEvents();
    }

    bindEvents() {
        const searchInput = document.querySelector('.search-box input');
        const genreBtns = document.querySelectorAll('.genre-filter-btn');
        const yearSelect = document.querySelector('select[name="year"]');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                // 200ms 防抖：避免每次按键都重新渲染
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.searchQuery = e.target.value.toLowerCase().trim();
                    this.applyFilters();
                }, 200);
            });
        }

        genreBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const genre = btn.dataset.genre;
                if (this.selectedGenre === genre) {
                    this.selectedGenre = null;
                    btn.classList.remove('active');
                } else {
                    document.querySelectorAll('.genre-filter-btn').forEach(b => b.classList.remove('active'));
                    this.selectedGenre = genre;
                    btn.classList.add('active');
                }
                this.applyFilters();
            });
        });

        if (yearSelect) {
            yearSelect.addEventListener('change', (e) => {
                this.selectedYear = e.target.value || null;
                this.applyFilters();
            });
        }
    }

    applyFilters() {
        this.filteredMovies = this.movies.filter(movie => {
            // 搜索匹配
            if (this.searchQuery) {
                const title = (movie.title || '').toLowerCase();
                const overview = (movie.overview || '').toLowerCase();
                const genres = (movie.genres || []).join(' ').toLowerCase();
                if (!title.includes(this.searchQuery) &&
                    !overview.includes(this.searchQuery) &&
                    !genres.includes(this.searchQuery)) {
                    return false;
                }
            }

            // 类型筛选
            if (this.selectedGenre) {
                if (!movie.genres || !movie.genres.includes(this.selectedGenre)) {
                    return false;
                }
            }

            // 年份筛选
            if (this.selectedYear) {
                if (movie.release_year !== parseInt(this.selectedYear)) {
                    return false;
                }
            }

            return true;
        });

        this.updateCounter();
        this.renderResults();
    }

    updateCounter() {
        const counter = document.getElementById('resultCounter');
        if (!counter) return;
        const total = this.movies.length;
        const shown = this.filteredMovies.length;
        if (this.searchQuery || this.selectedGenre || this.selectedYear) {
            counter.textContent = `显示 ${shown} / ${total} 部`;
            counter.classList.add('is-visible');
            counter.classList.toggle('is-empty', shown === 0);
        } else {
            counter.classList.remove('is-visible');
        }
    }

    renderResults() {
        const grid = document.querySelector('.movie-grid');
        if (!grid) return;

        if (this.filteredMovies.length === 0) {
            grid.innerHTML = `
                <div class="no-results">
                    <div class="icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7.5"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>
                    <p>没有找到匹配的电影</p>
                    <p class="hint">试试别的关键词、类型或年份</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredMovies.map(movie => this.createMovieCard(movie)).join('');
        // 重新绑定点击事件
        this.bindMovieCardEvents();
    }

    createMovieCard(movie) {
        const starSvg = '<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="none" style="vertical-align:-2px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>';
        const ratingBadge = movie.vote_average ? `${starSvg} ${Number(movie.vote_average).toFixed(1)}` : `${starSvg} N/A`;
        const genreTags = (movie.genres || []).slice(0, 2).map(g => `<span class="movie-genre-tag">${escapeHTML(g)}</span>`).join('');
        const safeTitle = escapeHTML(movie.title);
        const firstGenre = escapeHTML((movie.genres && movie.genres[0]) || '其他');
        const initial = escapeHTML((movie.title || '?')[0]);
        const posterClass = movie.poster_path ? 'movie-poster' : 'movie-poster movie-poster-placeholder';
        const posterDataAttr = movie.poster_path ? '' : `data-genre="${firstGenre}"`;
        const posterInner = movie.poster_path
            ? `<img class="movie-poster-img" src="${escapeHTML(movie.poster_path)}" alt="${safeTitle} 海报" loading="lazy" decoding="async">`
            : `<span>${initial}</span>`;

        return `
            <article class="movie-card" data-movie-id="${movie.movie_id}"
                     tabindex="0" role="button" aria-label="查看 ${safeTitle} 详情">
                <div class="${posterClass}" ${posterDataAttr}>
                    ${posterInner}
                    <div class="movie-poster-overlay">
                        <div class="movie-rating-badge">${ratingBadge}</div>
                        <div class="movie-genre-tags">${genreTags}</div>
                    </div>
                    <span class="movie-info-hint" aria-hidden="true">查看详情 →</span>
                </div>
                <h3>${safeTitle}</h3>
                <div class="movie-meta">${movie.release_year || '未知年份'}</div>
                <div class="movie-meta">${escapeHTML((movie.genres || []).join(', ') || '其他')}</div>
                <div style="margin-top: 10px;">
                    <span class="rating">${ratingBadge}</span>
                </div>
                <div class="rating-desc">${escapeHTML((movie.overview || '').length > 100 ? (movie.overview || '').substring(0, 100) + '...' : (movie.overview || ''))}</div>
            </article>`;
    }

    bindMovieCardEvents() {
        document.querySelectorAll('.movie-card').forEach(card => {
            bindMovieCardActivation(card, id => this.movies.find(m => m.movie_id === id));
        });
    }
}

// ========== 工具函数 ==========
function getGenreColor(genres) {
    const colors = {
        '科幻': 'linear-gradient(135deg, #0d1b2a, #1b0d2a)',
        '动作': 'linear-gradient(135deg, #2a0d0d, #3a1010)',
        '动画': 'linear-gradient(135deg, #1a0d1a, #2a1030)',
        '剧情': 'linear-gradient(135deg, #0a1628, #0d1b33)',
        '喜剧': 'linear-gradient(135deg, #2a1a0a, #331d0a)',
        '悬疑': 'linear-gradient(135deg, #1a0d2a, #220d33)',
        '惊悚': 'linear-gradient(135deg, #200a1a, #2a0d22)',
        '冒险': 'linear-gradient(135deg, #0a1a0d, #0d2210)',
        '奇幻': 'linear-gradient(135deg, #0a1a1a, #0d2022)',
        '爱情': 'linear-gradient(135deg, #2a0a1a, #331020)',
        '犯罪': 'linear-gradient(135deg, #18181a, #202020)',
        '其他': 'linear-gradient(135deg, #14141a, #1a1a22)'
    };
    const genre = (genres && genres[0]) || '其他';
    return colors[genre] || colors['其他'];
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}

// ========== 电影卡片交互（点击 + 键盘） ==========
function bindMovieCardActivation(card, findMovie) {
    const open = () => {
        const movieId = parseInt(card.dataset.movieId);
        const movie = findMovie(movieId);
        if (movie && window.movieModal) {
            window.movieModal.open(movie);
        }
    };
    card.addEventListener('click', open);
    card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            // role=button 下 Space 也应触发；阻止默认滚动
            e.preventDefault();
            open();
        }
    });
    // 按下视觉反馈
    card.addEventListener('pointerdown', () => card.classList.add('is-pressed'));
    card.addEventListener('pointerup', () => card.classList.remove('is-pressed'));
    card.addEventListener('pointerleave', () => card.classList.remove('is-pressed'));
}

// ========== 用户菜单 ==========
function initUserMenu() {
    const userMenu = document.getElementById('userMenu');
    const userMenuTrigger = document.getElementById('userMenuTrigger');

    if (!userMenu || !userMenuTrigger) return;

    userMenuTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        userMenu.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
        if (!userMenu.contains(e.target)) {
            userMenu.classList.remove('open');
        }
    });

    // ESC 关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            userMenu.classList.remove('open');
        }
    });
}

// ========== 移动端菜单 ==========
function initMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileNav = document.getElementById('mobileNav');

    if (!mobileMenuBtn || !mobileNav) return;

    mobileMenuBtn.addEventListener('click', () => {
        mobileNav.classList.toggle('open');
    });

    // 点击链接后关闭菜单
    mobileNav.querySelectorAll('.mobile-nav-link').forEach(link => {
        link.addEventListener('click', () => {
            mobileNav.classList.remove('open');
        });
    });
}

function initLoginRequiredLinks() {
    document.querySelectorAll('.requires-login').forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            Toast.warning('请先选择用户登录');
        });
    });
}

// ========== 初始化 ==========
// ========== 鼠标光晕 — recommend-prompt 卡片 ==========
function initPromptGlow() {
    document.querySelectorAll('.recommend-prompt').forEach(prompt => {
        prompt.addEventListener('mousemove', (e) => {
            const rect = prompt.getBoundingClientRect();
            prompt.style.setProperty('--mouse-x', ((e.clientX - rect.left) / rect.width * 100).toFixed(1) + '%');
            prompt.style.setProperty('--mouse-y', ((e.clientY - rect.top) / rect.height * 100).toFixed(1) + '%');
        });
    });
}

// ========== 按钮 ripple 效果 ==========
function initButtonRipple() {
    document.addEventListener('pointerdown', (e) => {
        const btn = e.target.closest('.btn');
        if (!btn) return;
        const rect = btn.getBoundingClientRect();
        btn.style.setProperty('--ripple-x', `${e.clientX - rect.left}px`);
        btn.style.setProperty('--ripple-y', `${e.clientY - rect.top}px`);
        btn.classList.remove('is-clicked');
        void btn.offsetWidth; // restart animation
        btn.classList.add('is-clicked');
        setTimeout(() => btn.classList.remove('is-clicked'), 650);
    });
}

// ========== 数字 count-up 动画 ==========
function animateCountUp(el, target, duration = 800) {
    const start = 0;
    const startTime = performance.now();
    const isInt = Number.isInteger(target);

    function step(now) {
        const elapsed = now - startTime;
        const t = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
        const current = start + (target - start) * eased;
        el.textContent = isInt ? Math.floor(current).toLocaleString() : current.toFixed(1);
        if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

function initCountUp() {
    document.querySelectorAll('.count-up[data-target]').forEach(el => {
        const target = parseFloat(el.dataset.target);
        if (!isNaN(target)) animateCountUp(el, target);
    });
}

// ========== 触屏设备检测 ==========
// 手机/平板上没有物理键盘，全字母快捷键会误触；
// 但 iPad+键盘这类设备仍应支持，所以用 pointer: coarse 判断主输入是触屏。
function isTouchPrimaryDevice() {
    return window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
}

// ========== 渲染 Flask flash 消息为 toast ==========
function renderFlashedMessages() {
    const el = document.getElementById('flashed-messages');
    if (!el) return;
    const messages = JSON.parse(el.dataset.messages || '[]');
    const typeMap = { 'error': 'error', 'success': 'success', 'warning': 'warning', 'info': 'info', 'message': 'info' };
    messages.forEach(([cat, msg]) => {
        Toast.show(msg, typeMap[cat] || 'info', 5000);
    });
    el.remove();
}

// ========== 键盘快捷键 ==========
function initKeyboardShortcuts() {
    if (isTouchPrimaryDevice()) return;  // 触屏主设备不绑定
    document.addEventListener('keydown', (e) => {
        const tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key === 'Escape') return; // modal 自己处理

        const key = e.key.toLowerCase();
        const shortcuts = {
            'h': { href: '/', label: '首页' },
            'm': { href: '/movies', label: '探索电影' },
            'r': { href: '/recommend/' + (window.__CURRENT_USER_ID__ || ''), label: '我的推荐', requireLogin: true },
            'c': { href: '/charts/' + (window.__CURRENT_USER_ID__ || ''), label: '我的图表', requireLogin: true },
        };
        const sc = shortcuts[key];
        if (!sc) return;
        if (sc.requireLogin && !window.__CURRENT_USER_ID__) {
            Toast.warning('请先选择用户登录');
            return;
        }
        e.preventDefault();
        window.location.href = sc.href;
    });
}

// "/" 聚焦搜索框（仿 GitHub / Slack 的常用快捷键）
function initSlashToSearch() {
    const searchInput = document.querySelector('.search-box input');
    if (!searchInput) return;
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const tag = (e.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Cursor-aware hero glow
    initHeroGlow();

    // Recommend-prompt 卡片光晕
    initPromptGlow();

    // 按钮 ripple
    initButtonRipple();

    // 数字 count-up
    initCountUp();

    // 把 flash 消息转成 toast
    renderFlashedMessages();

    // 键盘快捷键
    initKeyboardShortcuts();
    initSlashToSearch();

    // 初始化用户菜单
    initUserMenu();

    // 初始化移动端菜单
    initMobileMenu();

    // 初始化未登录入口提示
    initLoginRequiredLinks();

    // 初始化星级评分
    document.querySelectorAll('.star-rating-input').forEach(container => {
        new StarRating(container);
    });

    // 初始化电影 Modal
    window.movieModal = new MovieModal();

    // 初始化电影搜索
    const moviesData = window.__MOVIES_DATA__ || [];
    if (moviesData.length > 0 && document.querySelector('.search-box')) {
        window.movieSearch = new MovieSearch();
        window.movieSearch.init(moviesData);
    }

    // 绑定电影卡片点击 + 键盘交互
    document.querySelectorAll('.movie-card').forEach(card => {
        bindMovieCardActivation(card, id => moviesData.find(m => m.movie_id === id));
    });

    // 登录欢迎提示
    const welcomeBanner = document.querySelector('.welcome-banner');
    if (welcomeBanner) {
        setTimeout(() => {
            Toast.info('欢迎回来！个性化推荐已为你准备好~');
        }, 800);
    }
});

// ========== 放映机光束 — Cursor-aware hero glow ==========
function initHeroGlow() {
    const hero = document.getElementById('heroGlow');
    if (!hero) return;
    const glow = document.createElement('div');
    glow.className = 'hero-cursor-glow';
    hero.appendChild(glow);
    hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        hero.style.setProperty('--mouse-x', ((e.clientX - rect.left) / rect.width * 100).toFixed(1) + '%');
        hero.style.setProperty('--mouse-y', ((e.clientY - rect.top) / rect.height * 100).toFixed(1) + '%');
    });
}

// ========== Flash 消息处理 ==========
window.showToast = function(message, type = 'info') {
    Toast.show(message, type);
};
