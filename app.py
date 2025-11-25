# app.py
from flask import Flask, render_template_string, request
import requests
from urllib.parse import urlencode
from datetime import datetime
import time
import random

app = Flask(__name__)

# ---------- CONFIG ----------
DOMAIN = "www.vinted.fr"

# Dictionnaire des marques
AVAILABLE_BRANDS = {
    "2367131": "Andersson Bell",
    "11814083": "Applied art forms",
    "2053426": "Auralee",
    "7373680": "Beams Plus",
    "6781847": "Cmmawear",
    "56974": "Comme des Garçons",
    "5589958": "Comme des Garçons Homme",
    "2318552": "Comme des Garçons Homme Plus",
    "1330138": "Comme des Garçons tricot",
    "17308095": "Diomene",
    "5204470": "Evan Kinori",
    "257216": "Fucking Awesome",
    "4461245": "GR10K",
    "428133": "Haven",
    "235040": "Junya Watanabe",
    "2441307": "Mfpen",
    "596562": "Nanamica",
    "165016": "Noah",
    "218132": "Our Legacy",
    "139960": "Palace",
    "222038": "Palace Skateboards",
    "19580903": "Pet Tree Kor",
    "3935554": "Post Archive Faction",
    "11333247": "Ranra",
    "8640622": "Rier",
    "600988": "Roa",
    "369700": "Sacai",
    "11442249": "Sage Nation",
    "4690051": "Stefan Cooke",
    "441": "Stussy",
    "14969": "Supreme",
    "3232772": "This is never that",
    "11119537": "USM Haller"
}

PER_PAGE = 50
ORDER = "newest_first"

# Cache: on évite d'interroger Vinted trop souvent (TTL en secondes)
CACHE_TTL = 25 

# Session globale (créée une seule fois)
SESSION = None
LAST_FETCH = None
LAST_ITEMS = []
LAST_BRANDS = None

HTML_TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Vinted Watch - Mode & Style</title>
    <meta http-equiv="refresh" content="25" id="auto-refresh">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-color: #09b6a2;
            --primary-hover: #089286;
            --text-primary: #1a1a1a;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --bg-primary: #ffffff;
            --bg-secondary: #f8fafc;
            --border-color: #e5e7eb;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --radius: 12px;
            --radius-lg: 16px;
        }

        [data-theme="dark"] {
            --text-primary: #f5f5f5;
            --text-secondary: #d1d5db;
            --text-muted: #9ca3af;
            --bg-primary: #2a2a2a;
            --bg-secondary: #3a3a3a;
            --border-color: #525252;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.3), 0 4px 6px -4px rgb(0 0 0 / 0.3);
        }

        [data-theme="dark"] body {
            background: linear-gradient(135deg, #1f1f1f 0%, #0d0d0d 100%);
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            min-height: 100vh;
            line-height: 1.6;
            color: var(--text-primary);
            transition: background 0.3s ease;
        }

        .header {
            background: var(--bg-primary);
            border-bottom: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }

        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }

        .logo-text {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .theme-toggle, .fullscreen-toggle {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 50px;
            padding: 0.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
        }

        .theme-toggle:hover, .fullscreen-toggle:hover {
            transform: scale(1.05);
            box-shadow: var(--shadow-sm);
        }

        .theme-toggle svg, .fullscreen-toggle svg {
            width: 20px;
            height: 20px;
            color: var(--text-primary);
            transition: all 0.3s ease;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #dcfdf7;
            color: #059669;
            border-radius: 50px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        [data-theme="dark"] .status-badge {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        /* Styles pour la popup de filtres */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            padding: 2rem;
            margin: 1rem;
            max-width: 800px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border-color);
            position: relative;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .modal-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .close-btn {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 0.5rem;
            border-radius: 50%;
            transition: all 0.2s ease;
        }

        .close-btn:hover {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .filter-actions {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }

        .filter-btn {
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border-radius: var(--radius);
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .filter-btn:hover {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }

        .brands-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 0.75rem;
            margin-bottom: 2rem;
        }

        .brand-checkbox {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: var(--radius);
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }

        .brand-checkbox:hover {
            background: #e0f7f4;
            border-color: var(--primary-color);
        }

        [data-theme="dark"] .brand-checkbox:hover {
            background: rgba(9, 182, 162, 0.1);
        }

        .brand-checkbox input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--primary-color);
        }

        .brand-checkbox.checked {
            background: #dcfdf7;
            border-color: var(--primary-color);
            color: var(--primary-color);
            font-weight: 500;
        }

        [data-theme="dark"] .brand-checkbox.checked {
            background: rgba(9, 182, 162, 0.2);
            color: #22c55e;
        }

        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }

        .apply-filter {
            padding: 0.75rem 2rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--radius);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.875rem;
        }

        .apply-filter:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .apply-filter:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
            transform: none;
        }

        .cancel-btn {
            padding: 0.75rem 2rem;
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.875rem;
        }

        .cancel-btn:hover {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-primary);
            border-radius: var(--radius);
            padding: 1.5rem;
            text-align: center;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .stat-card.clickable {
            cursor: pointer;
        }

        .stat-card.clickable:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
            font-weight: 500;
        }

        .stat-action {
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 0.5rem;
        }

        .items-grid {
            display: grid;
            gap: 1.5rem;
        }

        .item-card {
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            overflow: hidden;
            box-shadow: var(--shadow-md);
            transition: all 0.3s ease;
            border: 1px solid var(--border-color);
            position: relative;
        }

        .item-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }

        .item-content {
            display: flex;
            align-items: stretch;
        }

        .item-image-container {
            flex: 0 0 210px;
            position: relative;
            overflow: hidden;
        }

        .item-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }

        .item-card:hover .item-image {
            transform: scale(1.05);
        }

        .price-badge {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.1rem;
            backdrop-filter: blur(10px);
        }

        [data-theme="dark"] .price-badge {
            background: rgba(255, 255, 255, 0.9);
            color: #1a1a1a;
        }

        .item-details {
            flex: 1;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .item-header {
            margin-bottom: 1rem;
        }

        .item-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .item-size {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.75rem;
            background: #f3f4f6;
            color: var(--text-secondary);
            border-radius: 50px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        [data-theme="dark"] .item-size {
            background: var(--bg-secondary);
        }

        .seller-info {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin: 1rem 0;
            padding: 1rem;
            background: #f8fafc;
            border-radius: var(--radius);
            transition: all 0.3s ease;
        }

        [data-theme="dark"] .seller-info {
            background: var(--bg-secondary);
        }

        .seller-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--primary-color);
        }

        .seller-details {
            flex: 1;
        }

        .seller-name {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }

        .seller-rating {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }

        .stars {
            color: #fbbf24;
            font-size: 1rem;
        }

        .rating-text {
            color: var(--text-secondary);
            font-weight: 500;
        }

        .item-actions {
            display: flex;
            gap: 0.75rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: var(--radius);
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }

        .btn-primary {
            background: var(--primary-color);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }

        .footer-note {
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 3rem;
            padding: 2rem;
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header-content {
                padding: 1rem;
            }

            .item-content {
                flex-direction: column;
            }

            .item-image-container {
                flex: none;
                height: 250px;
            }

            .item-image {
                height: 100%;
            }

            .stats-bar {
                grid-template-columns: repeat(2, 1fr);
            }

            .item-actions {
                flex-direction: column;
            }

            .brands-grid {
                grid-template-columns: 1fr;
            }

            .modal-content {
                margin: 0.5rem;
                width: calc(100% - 1rem);
                max-height: 90vh;
            }
        }

        .loading-shimmer {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
        }

        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }

        .star.empty {
            color: #d1d5db;
        }

        .star.filled {
            color: #fbbf24;
        }

        .star.half {
            position: relative;
            display: inline-block;
            color: #d1d5db;
        }

        .star.half::before {
            content: '★';
            position: absolute;
            left: 0;
            width: 50%;
            overflow: hidden;
            color: #fbbf24;
        }

        [data-theme="dark"] .star.empty {
            color: #6b7280;
        }

        [data-theme="dark"] .star.filled {
            color: #fbbf24;
        }

        [data-theme="dark"] .star.half {
            color: #6b7280;
        }

        [data-theme="dark"] .star.half::before {
            color: #fbbf24;
        }

    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">V</div>
                <div class="logo-text">Vinted Watch</div>
            </div>
            <div class="header-right">
                <button class="theme-toggle" onclick="toggleTheme()" aria-label="Basculer le thème">
                    <svg class="sun-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                    </svg>
                    <svg class="moon-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: none;">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                    </svg>
                </button>
                <button class="fullscreen-toggle" onclick="toggleFullscreen()" aria-label="Basculer le plein écran">
                    <svg class="expand-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                    </svg>
                    <svg class="compress-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: none;">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9l6 6m0-6l-6 6M21 3l-6 6m0 0V4m0 5h5M3 21l6-6m0 0h-5m5 0v5"/>
                    </svg>
                </button>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    Mis à jour à {{ refresh_time }}
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-value">{{ items|length }}</div>
                <div class="stat-label">Articles affichés</div>
            </div>
            <div class="stat-card clickable" onclick="openBrandModal()">
                <div class="stat-value">{{ selected_brands|length }}</div>
                <div class="stat-label">Marques sélectionnées</div>
                <div class="stat-action">Cliquer pour modifier</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ cache_ttl }}s</div>
                <div class="stat-label">Cache TTL</div>
            </div>
        </div>

        <!-- Modal pour le filtre de marques -->
        <div id="brandModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">Filtrer par marques</h3>
                    <button class="close-btn" onclick="closeBrandModal()">&times;</button>
                </div>
                
                <form method="GET" id="brand-filter-form">
                    <div class="filter-actions">
                        <button type="button" class="filter-btn" onclick="selectAllBrands()">Tout sélectionner</button>
                        <button type="button" class="filter-btn" onclick="clearAllBrands()">Tout désélectionner</button>
                    </div>
                    
                    <div class="brands-grid">
                        {% for brand_id, brand_name in available_brands.items() %}
                        <label class="brand-checkbox {% if brand_id in selected_brands %}checked{% endif %}">
                            <input type="checkbox" 
                                   name="brands" 
                                   value="{{ brand_id }}" 
                                   {% if brand_id in selected_brands %}checked{% endif %}
                                   onchange="updateBrandSelection(this)">
                            <span>{{ brand_name }}</span>
                        </label>
                        {% endfor %}
                    </div>
                    
                    <div class="modal-actions">
                        <button type="button" class="cancel-btn" onclick="closeBrandModal()">Annuler</button>
                        <button type="submit" class="apply-filter">Appliquer les filtres</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="items-grid">
            {% for it in items %}
            <article class="item-card">
                <div class="item-content">
                    <div class="item-image-container">
                        <img src="{{ it.photo }}" 
                             alt="Photo de {{ it.title }}" 
                             class="item-image"
                             onerror="">
                    </div>
                    <div class="item-details">
                        <div class="item-header">
                            <h2 class="item-title">{{ it.title }}</h2>
                            {% if it.size %}
                            <div class="item-size">
                                <span>👕</span> {{ it.size }}
                                <div class="price-badge">{{ it.price }}</div>
                            </div>
                            {% endif %}
                        </div>

                        <div class="seller-info">
                            <img src="{{ it.seller_avatar }}" 
                                 alt="Avatar de {{ it.seller_name }}" 
                                 class="seller-avatar"
                                 onerror="">
                            <div class="seller-details">
                                <div class="seller-name">{{ it.seller_name }}</div>
                                <div class="seller-rating">
                                    <span class="stars">{{ it.seller_stars|safe }}</span>
                                    <span class="rating-text">{{ it.seller_rating_display }}</span>
                                </div>
                            </div>
                        </div>

                        <div class="item-actions">
                            <a href="{{ it.url }}" target="_blank" class="btn btn-primary">
                                Voir l'article
                            </a>
                            <button class="btn btn-secondary" onclick="navigator.share ? navigator.share({title: '{{ it.title }}', url: '{{ it.url }}'}) : navigator.clipboard.writeText('{{ it.url }}')">
                                Partager
                            </button>
                        </div>
                    </div>
                </div>
            </article>
            {% endfor %}
        </div>

        <div class="footer-note">
            <p><strong>🤖 Vinted Watch</strong> - Surveillance automatique des nouvelles annonces</p>
            <p>Cache mis à jour toutes les {{ cache_ttl }} secondes pour éviter les limitations</p>
            <p>{{ selected_brands|length }} marque(s) sélectionnée(s) sur {{ available_brands|length }} disponibles</p>
        </div>
    </div>

    <script>
        // Prévenir le flash blanc en appliquant le thème AVANT le chargement
        (function() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', theme);
        })();

        // Gestion du thème
        function toggleTheme() {
            const html = document.documentElement;
            const sunIcon = document.querySelector('.sun-icon');
            const moonIcon = document.querySelector('.moon-icon');
            
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            if (newTheme === 'dark') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        }

        // Gestion du plein écran
        function toggleFullscreen() {
            const expandIcon = document.querySelector('.expand-icon');
            const compressIcon = document.querySelector('.compress-icon');
            
            if (!document.fullscreenElement) {
                // Entrer en plein écran
                document.documentElement.requestFullscreen().then(() => {
                    expandIcon.style.display = 'none';
                    compressIcon.style.display = 'block';
                    // Sauvegarder l'état plein écran
                    localStorage.setItem('fullscreenMode', 'true');
                }).catch(err => {
                    console.log('Erreur plein écran:', err);
                });
            } else {
                // Quitter le plein écran
                document.exitFullscreen().then(() => {
                    expandIcon.style.display = 'block';
                    compressIcon.style.display = 'none';
                    // Supprimer l'état plein écran
                    localStorage.removeItem('fullscreenMode');
                }).catch(err => {
                    console.log('Erreur sortie plein écran:', err);
                });
            }
        }

        // Écouter les changements de plein écran (pour gérer les raccourcis clavier)
        document.addEventListener('fullscreenchange', function() {
            const expandIcon = document.querySelector('.expand-icon');
            const compressIcon = document.querySelector('.compress-icon');
            
            if (document.fullscreenElement) {
                expandIcon.style.display = 'none';
                compressIcon.style.display = 'block';
                localStorage.setItem('fullscreenMode', 'true');
            } else {
                expandIcon.style.display = 'block';
                compressIcon.style.display = 'none';
                localStorage.removeItem('fullscreenMode');
            }
        });

        // Restaurer le plein écran au chargement de la page
        function initFullscreen() {
            const fullscreenSaved = localStorage.getItem('fullscreenMode');
            if (fullscreenSaved === 'true' && !document.fullscreenElement) {
                // Petit délai pour éviter les problèmes de timing
                setTimeout(() => {
                    document.documentElement.requestFullscreen().catch(err => {
                        console.log('Impossible de restaurer le plein écran:', err);
                        localStorage.removeItem('fullscreenMode');
                    });
                }, 100);
            }
        }

        // Initialisation du thème au chargement
        function initTheme() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? 'dark' : 'light');
            
            const html = document.documentElement;
            const sunIcon = document.querySelector('.sun-icon');
            const moonIcon = document.querySelector('.moon-icon');
            
            html.setAttribute('data-theme', theme);
            
            if (theme === 'dark') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        }

        // Gestion de la modal
        function openBrandModal() {
            document.getElementById('brandModal').classList.add('show');
            document.body.style.overflow = 'hidden';
            // Désactiver le refresh automatique pendant que la modal est ouverte
            disableAutoRefresh();
        }

        function closeBrandModal() {
            document.getElementById('brandModal').classList.remove('show');
            document.body.style.overflow = 'auto';
            // Réactiver le refresh automatique
            enableAutoRefresh();
        }

        // Gestion du refresh automatique
        function disableAutoRefresh() {
            const refreshMeta = document.getElementById('auto-refresh');
            if (refreshMeta) {
                refreshMeta.setAttribute('data-content', refreshMeta.getAttribute('content'));
                refreshMeta.removeAttribute('content');
            }
        }

        function enableAutoRefresh() {
            const refreshMeta = document.getElementById('auto-refresh');
            if (refreshMeta && refreshMeta.hasAttribute('data-content')) {
                refreshMeta.setAttribute('content', refreshMeta.getAttribute('data-content'));
                refreshMeta.removeAttribute('data-content');
            }
        }

        // Fermer la modal en cliquant à l'extérieur
        window.onclick = function(event) {
            const modal = document.getElementById('brandModal');
            if (event.target === modal) {
                closeBrandModal();
            }
        }

        // Fermer avec Escape
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const modal = document.getElementById('brandModal');
                if (modal && modal.classList.contains('show')) {
                    closeBrandModal();
                }
            }
        });

        // Gestion des filtres de marques
        function updateBrandSelection(checkbox) {
            const label = checkbox.closest('.brand-checkbox');
            if (checkbox.checked) {
                label.classList.add('checked');
            } else {
                label.classList.remove('checked');
            }
        }

        function selectAllBrands() {
            const checkboxes = document.querySelectorAll('input[name="brands"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                checkbox.closest('.brand-checkbox').classList.add('checked');
            });
        }

        function clearAllBrands() {
            const checkboxes = document.querySelectorAll('input[name="brands"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                checkbox.closest('.brand-checkbox').classList.remove('checked');
            });
        }

        // Variables globales pour gérer les nouveaux items (stockage persistant)
        let previousItemIds = JSON.parse(localStorage.getItem('vintedWatchItemIds') || '[]');
        let isFirstLoad = localStorage.getItem('vintedWatchFirstLoad') !== 'false';

        // Amélioration de l'expérience utilisateur
        document.addEventListener('DOMContentLoaded', function() {
            // Initialiser le thème
            initTheme();
            
            // Initialiser le plein écran
            initFullscreen();
            
            // Récupérer les IDs des items actuels
            const currentItems = Array.from(document.querySelectorAll('.item-card'));
            const currentItemIds = currentItems.map(card => {
                const url = card.querySelector('.btn-primary').href;
                return url.split('/').pop(); // Extraire l'ID de l'URL
            });
            
            if (isFirstLoad) {
                // Animation d'apparition normale au premier chargement
                currentItems.forEach((card, index) => {
                    card.style.animationDelay = `${index * 0.1}s`;
                    card.style.animation = 'fadeInUp 0.6s ease forwards';
                });
                localStorage.setItem('vintedWatchFirstLoad', 'false');
            } else {
                // Détecter les nouveaux items
                const newItemIds = currentItemIds.filter(id => !previousItemIds.includes(id));
                
                if (newItemIds.length > 0) {
                    // Il y a de nouveaux items
                    currentItems.forEach((card, index) => {
                        const url = card.querySelector('.btn-primary').href;
                        const itemId = url.split('/').pop();
                        
                        if (newItemIds.includes(itemId)) {
                            // Nouveau item - animation depuis le haut
                            card.classList.add('new-item');
                            card.style.animation = 'slideInFromTop 0.8s ease forwards';
                        } else {
                            // Item existant - animation de glissement vers le bas
                            card.classList.add('existing-item');
                            card.style.animation = 'slideDown 0.8s ease forwards';
                        }
                    });
                }
            }
            
            // Sauvegarder les IDs actuels
            localStorage.setItem('vintedWatchItemIds', JSON.stringify(currentItemIds));

            // Gestion des erreurs d'images avec retry
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                img.addEventListener('error', function() {
                    if (!this.hasAttribute('data-retry')) {
                        this.setAttribute('data-retry', 'true');
                        setTimeout(() => {
                            this.src = this.src;
                        }, 2000);
                    }
                });
            });
        });

        // Animation CSS pour l'apparition
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideInFromTop {
                from {
                    opacity: 0;
                    transform: translateY(-100px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideDown {
                from {
                    transform: translateY(0);
                }
                to {
                    transform: translateY(0);
                }
            }

            .new-item {
                position: relative;
                z-index: 10;
                box-shadow: 0 0 20px rgba(9, 182, 162, 0.3) !important;
                border: 2px solid var(--primary-color) !important;
            }

            .existing-item {
                transition: transform 0.8s ease;
            }

            /* Effet de surbrillance pour les nouveaux items */
            .new-item::before {
                content: 'NOUVEAU';
                position: absolute;
                top: -5px;
                left: 20px;
                background: var(--primary-color);
                color: white;
                padding: 4px 12px;
                border-radius: 50px;
                font-size: 0.75rem;
                font-weight: 700;
                z-index: 20;
                animation: pulse 2s infinite;
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
"""


def build_url(selected_brands):
    base = f"https://{DOMAIN}/api/v2/catalog/items"
    params = {"order": ORDER, "per_page": str(PER_PAGE)}
    if selected_brands:
        params["brand_ids"] = ",".join(selected_brands)
    return base + "?" + urlencode(params)


def make_session():
    """Crée une session requests avec headers réalistes et charge la page d'accueil."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    })
    try:
        # Visite la page accueil pour récupérer des cookies anti-bot
        s.get(f"https://{DOMAIN}/", timeout=12)
        time.sleep(random.uniform(0.2, 0.6))
    except Exception:
        # On ignore les erreurs de chargement initial
        pass
    return s


def normalize_photo_url(photo_url: str) -> str:
    """Normalise l'URL d'image (préfixe https: si nécessaire)."""
    if not photo_url:
        return ""
    photo_url = str(photo_url).strip()
    if photo_url.startswith("//"):
        return "https:" + photo_url
    if photo_url.startswith("/"):
        return "https://" + DOMAIN + photo_url
    return photo_url


def format_price(price_str: str = None, price_numeric=None, currency: str = None) -> str:
    """Formate proprement le prix pour l'affichage (robuste).

    Accepte dict, str, None. Retourne une chaîne prête pour affichage (ex: "25,00 €").
    """
    val = None

    # Si price_str est un dict, on récupère amount/currency
    if isinstance(price_str, dict):
        price_numeric = price_numeric or price_str.get("amount") or price_str.get("value")
        currency = currency or price_str.get("currency") or price_str.get("currency_code")
        price_str = None

    # Essayer price_numeric
    if price_numeric is not None:
        try:
            val = float(price_numeric)
        except Exception:
            val = None

    # Sinon tenter d'extraire depuis la string
    if val is None and isinstance(price_str, str) and price_str:
        cleaned = "".join(ch if (ch.isdigit() or ch in ",.") else "" for ch in price_str)
        if cleaned:
            cleaned = cleaned.replace(',', '.')
            try:
                val = float(cleaned)
            except Exception:
                val = None

    if val is None:
        return str(price_str or "").strip()

    s = f"{val:,.2f}"
    s = s.replace(',', ' ').replace('.', ',')

    cur = (currency or "").upper()
    if cur in ("EUR", "€", "EURO") or DOMAIN.endswith(".fr"):
        return f"{s} €"
    if cur:
        return f"{s} {cur}"
    return s


def build_star_string(rating, max_stars=5):
    try:
        r = float(rating)
    except Exception:
        return "—"

    r = max(0.0, min(float(max_stars), r))  # clamp
    filled = int(r)
    half = 1 if (r - filled) >= 0.5 else 0
    empty = max_stars - filled - half

    stars_html = '★' * filled
    if half:
        stars_html += '⭐'
    stars_html += '☆' * empty

    return stars_html


def fetch_items_from_vinted(session, url: str):
    headers = {
        "Referer": f"https://{DOMAIN}/",
        "Origin": f"https://{DOMAIN}",
        "X-Requested-With": "XMLHttpRequest",
    }
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            r = session.get(url, headers=headers, timeout=18)
        except Exception as e:
            # erreur réseau -> courte pause puis retry
            time.sleep(random.uniform(2.0, 6.0))
            continue

        if r.status_code == 403:
            # attendre un peu plus longtemps si 403 pour éviter blocage
            time.sleep(random.randint(20, 60))
            continue

        try:
            data = r.json()
        except Exception as e:
            snippet = (r.text or "")[:500].replace("\n", " ")
            # petite pause puis retry
            time.sleep(random.uniform(5.0, 10.0))
            continue

        return data.get("items", [])

    # si on échoue
    return []


def fetch_items(selected_brands):
    global SESSION, LAST_FETCH, LAST_ITEMS, LAST_BRANDS
    if SESSION is None:
        SESSION = make_session()

    now = datetime.now()
    brands_changed = LAST_BRANDS != selected_brands
    
    if not brands_changed and LAST_FETCH and (now - LAST_FETCH).total_seconds() < CACHE_TTL:
        return LAST_ITEMS

    url = build_url(selected_brands)
    items_raw = fetch_items_from_vinted(SESSION, url)

    items = []
    for it in items_raw:
        photo_url = ""
        if it.get("photo"):
            p = it["photo"]
            if isinstance(p, dict):
                photo_url = p.get("url") or p.get("url_thumb") or ""
            elif isinstance(p, str):
                photo_url = p
        elif it.get("photos"):
            photos = it["photos"]
            if isinstance(photos, list) and photos:
                first = photos[0]
                if isinstance(first, dict):
                    photo_url = (
                        first.get("url_fullxfull")
                        or first.get("url")
                        or first.get("url_300")
                        or first.get("url_thumb")
                        or ""
                    )
        photo_url = normalize_photo_url(photo_url)

        title = it.get("title") or it.get("brand_title") or "Annonce"

        price_numeric = it.get("price_numeric") or it.get("price_amount") or None
        currency = it.get("currency") or it.get("price_currency") or None
        price_raw = it.get("price") or it.get("price_info") or None
        price = format_price(price_raw, price_numeric, currency)

        size = it.get("size_title") or ""
        url_item = f"https://{DOMAIN}/items/{it.get('id')}"

        user_info = it.get("user") or it.get("seller") or it.get("owner") or {}
        seller_name = (
            (user_info.get("display_name") if isinstance(user_info, dict) else None)
            or (user_info.get("login") if isinstance(user_info, dict) else None)
            or (user_info.get("username") if isinstance(user_info, dict) else None)
            or (user_info.get("nickname") if isinstance(user_info, dict) else None)
            or (user_info.get("title") if isinstance(user_info, dict) else None)
            or "Utilisateur"
        )

        seller_avatar = ""
        if isinstance(user_info, dict):
            a = user_info.get("avatar") or user_info.get("photo") or user_info.get("thumb")
            if isinstance(a, dict):
                seller_avatar = a.get("url") or a.get("url_thumb") or a.get("thumb") or ""
            elif isinstance(a, str):
                seller_avatar = a
        seller_avatar = normalize_photo_url(seller_avatar)

        seller_rating = None
        if isinstance(user_info, dict):
            for key in ("rating_average", "avg_rating", "score", "rating", "rating_value"):
                if key in user_info and user_info.get(key) is not None:
                    seller_rating = user_info.get(key)
                    break
        if seller_rating is None and isinstance(it.get("user_stats"), dict):
            us = it.get("user_stats")
            for key in ("rating_average", "avg_rating", "rating"):
                if key in us and us.get(key) is not None:
                    seller_rating = us.get(key)
                    break

        if seller_rating is None:
            seller_rating_display = "—"
            seller_stars = "—"
        else:
            try:
                sr = float(seller_rating)
            except Exception:
                sr = None
            if sr is None:
                seller_rating_display = str(seller_rating)
                seller_stars = "—"
            else:
                seller_rating_display = f"{sr:.1f}/5"
                seller_stars = build_star_string(sr, max_stars=5)

        items.append({
            "title": title,
            "price": price,
            "size": size,
            "url": url_item,
            "photo": photo_url,
            "seller_name": seller_name,
            "seller_avatar": seller_avatar,
            "seller_rating_display": seller_rating_display,
            "seller_stars": seller_stars,
        })

    LAST_ITEMS = items
    LAST_FETCH = datetime.now()
    LAST_BRANDS = selected_brands
    return items


@app.route("/")
def index():
    # Récupérer les marques sélectionnées depuis les paramètres GET
    selected_brands = request.args.getlist('brands')
    
    # Si aucune marque n'est sélectionnée, utiliser toutes les marques par défaut
    if not selected_brands:
        selected_brands = list(AVAILABLE_BRANDS.keys())
    
    items = fetch_items(selected_brands)
    refresh_time = datetime.now().strftime("%H:%M:%S")
    
    return render_template_string(
        HTML_TEMPLATE, 
        items=items, 
        refresh_time=refresh_time, 
        cache_ttl=CACHE_TTL,
        available_brands=AVAILABLE_BRANDS,
        selected_brands=selected_brands
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
