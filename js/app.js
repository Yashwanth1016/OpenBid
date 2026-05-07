/* ============================================================
   OPENBID — Shared State & Utilities (app.js)
   ============================================================ */

// ─── State ──────────────────────────────────────────────────
const State = {
    currentUser: JSON.parse(sessionStorage.getItem('ob_user') || 'null'),
    items: [],

    async loadItems() {
        try {
            const res = await fetch('/api/items');
            const data = await res.json();
            this.items = data.items || [];
        } catch (e) {
            console.error("Error loading items:", e);
        }
        return this.items;
    },

    setUser(user) {
        this.currentUser = user;
        sessionStorage.setItem('ob_user', JSON.stringify(user));
    },

    logout() {
        this.currentUser = null;
        sessionStorage.removeItem('ob_user');
    },

    getItem(id) {
        return this.items.find(i => i.id === id);
    },

    async addItem(item) {
        try {
            const res = await fetch('/api/items', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });
            const data = await res.json();
            this.items.push(data.item || item);
            return data;
        } catch (e) {
            console.error("Error adding item:", e);
        }
    },

    getRoomItems(room) {
        return this.items.filter(i => i.room === room && i.status !== 'sold');
    },

    getRoomForPrice(price) {
        if (price < 5000) return 1;
        if (price < 50000) return 2;
        if (price < 100000) return 3;
        if (price < 200000) return 4;
        if (price < 500000) return 5;
        return 6;
    },

    getTokenInRoom(room) {
        const roomItems = this.items.filter(i => i.room === room);
        return roomItems.length + 1;
    },

    async addNotify(itemId, user) {
        try {
            await fetch('/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ itemId, user })
            });
        } catch (e) {
            console.error("Error adding notification", e);
        }
    },

    async isNotified(itemId, user) {
        try {
            const res = await fetch('/api/notify/' + itemId);
            const data = await res.json();
            return data.users.includes(user);
        } catch (e) {
            return false;
        }
    },

    async markSold(itemId) {
        try {
            await fetch('/api/items/' + itemId + '/sold', { method: 'POST' });
            const item = this.getItem(itemId);
            if (item) item.status = 'sold';
        } catch (e) {
            console.error("Error marking sold", e);
        }
    }
};

// ─── Toast Notifications ────────────────────────────────────
function showToast(title, msg, duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<div class="toast-title">🔔 ${title}</div>${msg}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

function checkPendingNotifications() {
    // Omitting client-side pending notifications for simplicity 
    // as state is now in backend.
}

// ─── Sidebar ─────────────────────────────────────────────────
function renderTopNav(activePage) {
    const user = State.currentUser;
    return `
    <nav class="topnav">
        <div class="logo">OPENBID</div>
        <div class="nav-right">
            ${user ? `<span class="nav-user">👤 ${user.username}</span>` : ''}
            <div class="profile-icon" onclick="toggleSidebar()">
                <svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
            </div>
        </div>
    </nav>
    <div class="sidebar" id="profileSidebar">
        <span class="sidebar-close" onclick="toggleSidebar()">&times;</span>
        <h3>USER PROFILE</h3>
        <div class="user-info" style="margin-bottom:20px;">
            <p>Name: <span>${user ? user.fullName || user.username : '—'}</span></p>
            <p>Email: <span>${user ? user.email || '—' : '—'}</span></p>
            <p>Phone: <span>${user ? user.phone || '—' : '—'}</span></p>
        </div>
        <h3>MY LISTED ITEMS</h3>
        <div id="sidebar-items">
            ${renderSidebarItems()}
        </div>
        <br>
        <button class="btn-outline" style="width:100%" onclick="doLogout()">LOGOUT</button>
    </div>`;
}

function renderSidebarItems() {
    const user = State.currentUser;
    if (!user) return '';
    const mine = State.items.filter(i => i.seller === user.username);
    if (!mine.length) return '<p style="color:var(--text-muted);font-family:Arial;font-size:0.82rem;">No items listed yet.</p>';
    return mine.map(i => `
        <div class="sidebar-item">
            <span>${i.name}</span>
            <span class="price">₹${Number(i.basePrice).toLocaleString()}</span>
        </div>`).join('');
}

function toggleSidebar() {
    document.getElementById('profileSidebar').classList.toggle('active');
}

function doLogout() {
    State.logout();
    window.location.href = 'index.html';
}

// ─── Auth Guard ──────────────────────────────────────────────
function requireAuth() {
    if (!State.currentUser) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// ─── Terms & Conditions HTML ─────────────────────────────────
const TERMS_HTML = `
<ol>
  <li>Every seller using this auction platform confirms that the products uploaded by them are legal, genuine, and authorized for sale.</li>
  <li>Sellers are fully responsible for the ownership, originality, and legality of the items listed on the platform.</li>
  <li>The auction platform acts only as an online medium between buyers and sellers and does not verify every product physically.</li>
  <li>Any illegal, stolen, duplicate, prohibited, or unauthorized item is strictly not allowed on the platform.</li>
  <li>By uploading an item, the seller agrees that all product details and descriptions provided are true and accurate.</li>
  <li>Buyers and bidders are advised to verify product details carefully before placing bids.</li>
  <li>The highest bidder must complete payment within the allotted payment time after winning the auction.</li>
  <li>If the highest bidder fails to complete the payment within the given time, the product may be transferred to the next highest bidder.</li>
  <li>The platform owners are not responsible for disputes regarding product quality, originality, delivery, or legality between buyers and sellers.</li>
  <li>Fake bidding, fraud, misuse of the platform, or illegal activities may lead to account suspension or permanent blocking.</li>
  <li>All users agree to follow local laws and regulations related to buying and selling products while using this platform.</li>
  <li>By using this auction platform, both buyers and sellers accept all the above terms and conditions.</li>
</ol>`;

// ─── Room Metadata ───────────────────────────────────────────
const ROOMS = [
    { id:1, label:'Room 1', range:'Below ₹5,000',       min:0,      max:4999,  color:'#7cb9e8' },
    { id:2, label:'Room 2', range:'₹5,000 – ₹50,000',   min:5000,   max:49999, color:'#90ee90' },
    { id:3, label:'Room 3', range:'₹50,000 – ₹1,00,000',min:50000,  max:99999, color:'#ffdf00' },
    { id:4, label:'Room 4', range:'₹1,00,000 – ₹2,00,000',min:100000,max:199999,color:'#ff8c00'},
    { id:5, label:'Room 5', range:'₹2,00,000 – ₹5,00,000',min:200000,max:499999,color:'#ff6b6b'},
    { id:6, label:'Room 6', range:'Above ₹5,00,000',    min:500000, max:Infinity,color:'#cc4dcc'},
];

const CATEGORIES = ['Electronics','Home Appliances','Fashion','Mobiles','Sports','Books'];
