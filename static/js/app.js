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
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close">×</button>
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
        const posterUrl = movie.poster_path || `/posters/${movie.movie_id}.jpg`;
        posterEl.style.backgroundImage = `url('${posterUrl}')`;
        posterEl.classList.remove('modal-poster-placeholder');
        posterEl.innerHTML = '';
        posterEl.onerror = () => {
            posterEl.style.backgroundImage = 'none';
            posterEl.classList.add('modal-poster-placeholder');
            posterEl.innerHTML = `<span>${movie.title[0]}</span>`;
            posterEl.style.background = this.getGenreColor(movie.genres);
        };

        // 元信息
        const metaItems = [];
        if (movie.release_year) metaItems.push(`📅 ${movie.release_year}`);
        if (movie.popularity) metaItems.push(`🔥 ${Math.round(movie.popularity)}`);
        content.querySelector('.modal-meta').innerHTML = metaItems.map(m => `<span>${m}</span>`).join('');

        // 类型标签
        const genresHtml = (movie.genres || []).map(g =>
            `<span class="modal-genre-tag">${g}</span>`
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
        const modalBody = content.querySelector('.modal-body');
        if (window.__CURRENT_USER_ID__) {
            const userRating = this.getUserRating(movie.movie_id);
            modalBody.innerHTML = `
                <h3>我的评分</h3>
                <div class="modal-rating-form" data-movie-id="${movie.movie_id}">
                    <div class="star-rating-input" style="flex-direction: row; align-items: center; gap: 12px;">
                        <div class="stars">
                            ${[1,2,3,4,5].map(n => `<span class="star ${n <= userRating ? 'selected' : ''}" data-value="${n}" style="font-size: 28px; color: ${n <= userRating ? '#ffc107' : '#333'}; cursor: pointer;">★</span>`).join('')}
                        </div>
                        <span class="rating-text" style="color: #888; font-size: 13px;">${userRating ? '已评分' : '点击星星评分'}</span>
                    </div>
                    <input type="hidden" class="hidden-rating-input" value="${userRating}">
                </div>
            `;
            // 绑定评分事件
            modalBody.querySelectorAll('.star').forEach(star => {
                star.addEventListener('click', () => this.handleRating(movie.movie_id, parseInt(star.dataset.value)));
                star.addEventListener('mouseenter', () => {
                    const val = parseInt(star.dataset.value);
                    modalBody.querySelectorAll('.star').forEach((s, i) => {
                        s.style.color = i < val ? '#ffc107' : '#333';
                    });
                });
                star.addEventListener('mouseleave', () => {
                    const current = parseInt(modalBody.querySelector('.hidden-rating-input').value) || userRating;
                    modalBody.querySelectorAll('.star').forEach((s, i) => {
                        s.style.color = i < current ? '#ffc107' : '#333';
                    });
                });
            });
        } else {
            modalBody.innerHTML = '<p style="color: #888; text-align: center; padding: 10px;">登录后可评分</p>';
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
        // 提交评分
        fetch('/api/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `movie_id=${movieId}&rating=${rating}`
        }).then(response => response.json())
          .then(data => {
            if (data.error) {
                Toast.error(data.error);
            } else {
                Toast.success(`评分成功：${rating} 星！`);
                // 更新本地评分数据
                if (!window.__USER_RATINGS__) window.__USER_RATINGS__ = {};
                window.__USER_RATINGS__[movieId] = rating;
                // 更新星星显示
                const modalBody = document.querySelector('.modal-body');
                modalBody.querySelector('.hidden-rating-input').value = rating;
                modalBody.querySelector('.rating-text').textContent = '已评分';
                modalBody.querySelectorAll('.star').forEach((s, i) => {
                    s.style.color = i < rating ? '#ffc107' : '#333';
                });
            }
          }).catch(() => {
            Toast.error('评分失败，请重试');
          });
    }

    close() {
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    getGenreColor(genres) {
        const colors = {
            '科幻': 'linear-gradient(135deg, #1a237e, #4a148c)',
            '动作': 'linear-gradient(135deg, #b71c1c, #c62828)',
            '动画': 'linear-gradient(135deg, #880e4f, #ad1457)',
            '剧情': 'linear-gradient(135deg, #0d47a1, #1565c0)',
            '喜剧': 'linear-gradient(135deg, #e65100, #ff6d00)',
            '悬疑': 'linear-gradient(135deg, #311b92, #512da8)',
            '惊悚': 'linear-gradient(135deg, #4a148c, #6a1b9a)',
            '冒险': 'linear-gradient(135deg, #1b5e20, #2e7d32)',
            '奇幻': 'linear-gradient(135deg, #006064, #00838f)',
            '爱情': 'linear-gradient(135deg, #ad1457, #c2185b)',
            '犯罪': 'linear-gradient(135deg, #263238, #37474f)',
            '其他': 'linear-gradient(135deg, #37474f, #455a64)'
        };
        const genre = (genres && genres[0]) || '其他';
        return colors[genre] || colors['其他'];
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
    }

    init(movies) {
        this.movies = movies;
        this.filteredMovies = [...movies];
        this.bindEvents();
    }

    bindEvents() {
        const searchInput = document.querySelector('.search-box input');
        const genreBtns = document.querySelectorAll('.genre-filter-btn');
        const yearSelect = document.querySelector('select[name="year"]');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase();
                this.applyFilters();
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
                const title = movie.title.toLowerCase();
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

        this.renderResults();
    }

    renderResults() {
        const grid = document.querySelector('.movie-grid');
        if (!grid) return;

        if (this.filteredMovies.length === 0) {
            grid.innerHTML = `
                <div class="no-results">
                    <div class="icon">🔍</div>
                    <p>没有找到匹配的电影</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredMovies.map(movie => this.createMovieCard(movie)).join('');
        // 重新绑定点击事件
        this.bindMovieCardEvents();
    }

    createMovieCard(movie) {
        const ratingBadge = movie.vote_average ? `⭐ ${Number(movie.vote_average).toFixed(1)}` : '⭐ N/A';
        const genreTags = (movie.genres || []).slice(0, 2).map(g => `<span class="movie-genre-tag">${g}</span>`).join('');
        const fallbackStyle = `background: ${getGenreColor(movie.genres)}`;
        const onerrorAttr = `onerror="this.style.backgroundImage='none'; this.classList.add('movie-poster-placeholder'); this.style.background='${fallbackStyle}'; this.innerHTML='<span>${movie.title[0]}</span><div class=\\'movie-poster-overlay\\'><div class=\\'movie-rating-badge\\'>${ratingBadge}</div></div>'"`;

        return `
            <div class="movie-card" data-movie-id="${movie.movie_id}">
                <div class="movie-poster" style="background-image: url('${movie.poster_path}')" ${onerrorAttr}>
                    <div class="movie-poster-overlay">
                        <div class="movie-rating-badge">${ratingBadge}</div>
                        <div class="movie-genre-tags">${genreTags}</div>
                    </div>
                </div>
                <h3>${movie.title}</h3>
                <div class="movie-meta">${movie.release_year || '未知年份'}</div>
                <div class="movie-meta">${(movie.genres || []).join(', ') || '其他'}</div>
                <div style="margin-top: 10px;">
                    <span class="rating">${ratingBadge}</span>
                </div>
                <div class="rating-desc">${((movie.overview || '').substring(0, 100)).replace(/</g, '&lt;').replace(/>/g, '&gt;')}...</div>
            </div>`;
    }

    bindMovieCardEvents() {
        document.querySelectorAll('.movie-card').forEach(card => {
            card.addEventListener('click', () => {
                const movieId = parseInt(card.dataset.movieId);
                const movie = this.movies.find(m => m.movie_id === movieId);
                if (movie) {
                    window.movieModal.open(movie);
                }
            });
        });
    }
}

// ========== 交互式图表 ==========
class InteractiveChart {
    constructor(canvasId, type, data, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.type = type;
        this.data = data;
        this.options = options;
        this.chart = null;
        this.init();
    }

    async init() {
        // 动态加载 Chart.js
        if (!window.Chart) {
            await this.loadChartJS();
        }
        this.render();
    }

    loadChartJS() {
        return new Promise((resolve) => {
            if (document.querySelector('script[src*="chart.js"]')) {
                resolve();
                return;
            }
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            script.onload = resolve;
            document.head.appendChild(script);
        });
    }

    render() {
        const ctx = this.canvas.getContext('2d');

        if (this.chart) {
            this.chart.destroy();
        }

        const config = this.getChartConfig();
        this.chart = new Chart(ctx, config);
    }

    getChartConfig() {
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#b0b0b0', font: { size: 12 } }
                }
            }
        };

        if (this.type === 'bar') {
            return {
                type: 'bar',
                data: {
                    labels: this.data.labels,
                    datasets: [{
                        label: this.data.label,
                        data: this.data.values,
                        backgroundColor: this.data.colors || 'rgba(233, 69, 96, 0.6)',
                        borderColor: this.data.colors || 'rgba(233, 69, 96, 1)',
                        borderWidth: 1,
                        borderRadius: 6
                    }]
                },
                options: {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#888' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#888' }
                        }
                    }
                }
            };
        }

        if (this.type === 'doughnut') {
            return {
                type: 'doughnut',
                data: {
                    labels: this.data.labels,
                    datasets: [{
                        data: this.data.values,
                        backgroundColor: this.data.colors,
                        borderWidth: 0
                    }]
                },
                options: {
                    ...baseOptions,
                    cutout: '60%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#b0b0b0', padding: 15, font: { size: 11 } }
                        }
                    }
                }
            };
        }

        return {};
    }

    updateData(newData) {
        this.data = newData;
        this.render();
    }
}

// ========== 工具函数 ==========
function getGenreColor(genres) {
    const colors = {
        '科幻': 'linear-gradient(135deg, #1a237e, #4a148c)',
        '动作': 'linear-gradient(135deg, #b71c1c, #c62828)',
        '动画': 'linear-gradient(135deg, #880e4f, #ad1457)',
        '剧情': 'linear-gradient(135deg, #0d47a1, #1565c0)',
        '喜剧': 'linear-gradient(135deg, #e65100, #ff6d00)',
        '悬疑': 'linear-gradient(135deg, #311b92, #512da8)',
        '惊悚': 'linear-gradient(135deg, #4a148c, #6a1b9a)',
        '冒险': 'linear-gradient(135deg, #1b5e20, #2e7d32)',
        '奇幻': 'linear-gradient(135deg, #006064, #00838f)',
        '爱情': 'linear-gradient(135deg, #ad1457, #c2185b)',
        '犯罪': 'linear-gradient(135deg, #263238, #37474f)',
        '其他': 'linear-gradient(135deg, #37474f, #455a64)'
    };
    const genre = (genres && genres[0]) || '其他';
    return colors[genre] || colors['其他'];
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

// ========== 页面转场动画 ==========
function initPageTransitions() {
    document.body.classList.add('page-loaded');
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 初始化用户菜单
    initUserMenu();

    // 初始化移动端菜单
    initMobileMenu();

    // 初始化页面转场
    initPageTransitions();

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

    // 绑定电影卡片点击事件
    document.querySelectorAll('.movie-card').forEach(card => {
        card.addEventListener('click', () => {
            const movieId = parseInt(card.dataset.movieId);
            const movie = moviesData.find(m => m.movie_id === movieId);
            if (movie && window.movieModal) {
                window.movieModal.open(movie);
            }
        });
    });

    // 绑定推荐卡片点击事件
    document.querySelectorAll('.rec-item').forEach(card => {
        card.addEventListener('click', () => {
            const movieId = parseInt(card.dataset.movieId);
            const movie = moviesData.find(m => m.movie_id === movieId);
            if (movie && window.movieModal) {
                window.movieModal.open(movie);
            }
        });
    });

    // 表单提交 Toast 提示
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('no-toast')) {
                setTimeout(() => {
                    Toast.success('提交成功！');
                }, 100);
            }
        });
    });

    // 换一批按钮
    document.querySelectorAll('.refresh-recs').forEach(btn => {
        btn.addEventListener('click', async function() {
            if (this.classList.contains('loading')) return;
            this.classList.add('loading');
            this.innerHTML = '<span class="spin">↻</span> 加载中...';

            // 模拟刷新
            await new Promise(resolve => setTimeout(resolve, 1000));

            this.classList.remove('loading');
            this.innerHTML = '<span>↻</span> 换一批';
            Toast.info('已为你换一批新推荐！');
        });
    });

    // 登录欢迎提示
    const welcomeBanner = document.querySelector('.welcome-banner');
    if (welcomeBanner) {
        setTimeout(() => {
            Toast.info('欢迎回来！个性化推荐已为你准备好~');
        }, 800);
    }
});

// ========== Flash 消息处理 ==========
window.showToast = function(message, type = 'info') {
    Toast.show(message, type);
};
