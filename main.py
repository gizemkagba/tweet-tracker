import flet as ft
import flet_charts as fch
import os
import json
import threading
import time
from datetime import datetime, timedelta
import pandas as pd

import db
from twitter_client import TwitterClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "mode": "twikit",
        "api_key": "",
        "api_secret": "",
        "access_token": "",
        "access_token_secret": "",
        "bearer_token": "",
        "twikit_username": "",
        "twikit_password": "",
        "twikit_email": ""
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def main(page: ft.Page):
    page.title = "X (Twitter) Tweet Tracker & Analytics"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1200
    page.window_height = 850
    page.window_min_width = 1000
    page.window_min_height = 700
    
    def show_toast(text):
        snack = ft.SnackBar(ft.Text(text), open=True)
        page.overlay.append(snack)
        page.update()
    
    # Initialize DB
    db.init_db()
    
    # Load configurations
    settings = load_settings()
    
    # State variables
    is_tracking = False
    log_messages = []
    
    # UI Component References
    stat_total_tweets = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400)
    stat_avg_likes = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)
    stat_avg_sentiment = ft.Text("0.0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
    stat_total_retweets = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PINK_400)
    
    log_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    progress_bar = ft.ProgressBar(value=0, visible=False, color=ft.Colors.CYAN_400)
    progress_text = ft.Text("Hazır", size=14, italic=True)
    
    # Charts Container references
    sentiment_chart_container = ft.Container(expand=True, alignment=ft.Alignment.CENTER)
    line_chart_container = ft.Container(expand=True, alignment=ft.Alignment.CENTER)
    keyword_chart_container = ft.Container(expand=True, alignment=ft.Alignment.CENTER)
    
    # Data Table reference
    tweets_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tarih")),
            ft.DataColumn(ft.Text("Kullanıcı Adı")),
            ft.DataColumn(ft.Text("Tweet İçeriği")),
            ft.DataColumn(ft.Text("Beğeni")),
            ft.DataColumn(ft.Text("Retweet")),
            ft.DataColumn(ft.Text("Duygu")),
        ],
        rows=[],
    )
    
    data_table_container = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    
    # Filter controls for data browser
    filter_keyword_dropdown = ft.Dropdown(label="Anahtar Kelime Filtresi", width=200, on_select=lambda e: refresh_data_browser())
    
    # Settings fields
    api_mode_dropdown = ft.Dropdown(
        label="Veri Çekme Modu",
        options=[
            ft.dropdown.Option("live", "Resmi API Modu (Bearer Token)"),
            ft.dropdown.Option("twikit", "Twikit Giriş Modu (Ücretsiz & Canlı)")
        ],
        value=settings.get("mode", "twikit"),
        on_select=lambda e: toggle_api_mode(e),
        width=400
    )
    
    api_key_field = ft.TextField(label="API Key", password=True, can_reveal_password=True, value=settings.get("api_key", ""), width=400)
    api_secret_field = ft.TextField(label="API Secret", password=True, can_reveal_password=True, value=settings.get("api_secret", ""), width=400)
    access_token_field = ft.TextField(label="Access Token", password=True, can_reveal_password=True, value=settings.get("access_token", ""), width=400)
    access_token_secret_field = ft.TextField(label="Access Token Secret", password=True, can_reveal_password=True, value=settings.get("access_token_secret", ""), width=400)
    bearer_token_field = ft.TextField(label="Bearer Token", password=True, can_reveal_password=True, value=settings.get("bearer_token", ""), width=400)
    
    twikit_user_field = ft.TextField(label="Twitter Kullanıcı Adı (Yedek Hesabınız)", value=settings.get("twikit_username", ""), width=400)
    twikit_pass_field = ft.TextField(label="Twitter Şifresi", password=True, can_reveal_password=True, value=settings.get("twikit_password", ""), width=400)
    twikit_email_field = ft.TextField(label="Twitter E-posta Adresi", value=settings.get("twikit_email", ""), width=400)
    
    api_fields_container = ft.Column(
        controls=[
            ft.Text("Twitter API v2 Kimlik Bilgileri", size=14, weight=ft.FontWeight.BOLD),
            api_key_field,
            api_secret_field,
            access_token_field,
            access_token_secret_field,
            bearer_token_field
        ],
        visible=(settings.get("mode") == "live")
    )
    
    twikit_fields_container = ft.Column(
        controls=[
            ft.Text("Twikit X Giriş Bilgileri (Yedek Hesabınız)", size=14, weight=ft.FontWeight.BOLD),
            twikit_user_field,
            twikit_pass_field,
            twikit_email_field
        ],
        visible=(settings.get("mode") == "twikit")
    )
    
    def toggle_api_mode(e):
        val = api_mode_dropdown.value
        api_fields_container.visible = (val == "live")
        twikit_fields_container.visible = (val == "twikit")
        page.update()
        
    def save_settings_click(e):
        settings["mode"] = api_mode_dropdown.value
        settings["api_key"] = api_key_field.value
        settings["api_secret"] = api_secret_field.value
        settings["access_token"] = access_token_field.value
        settings["access_token_secret"] = access_token_secret_field.value
        settings["bearer_token"] = bearer_token_field.value
        settings["twikit_username"] = twikit_user_field.value
        settings["twikit_password"] = twikit_pass_field.value
        settings["twikit_email"] = twikit_email_field.value
        save_settings(settings)
        show_toast("Ayarlar başarıyla kaydedildi!")

    # Helper: Refresh Dashboard Charts and Stats
    def refresh_dashboard():
        stats = db.get_overall_stats()
        stat_total_tweets.value = f"{stats['total_tweets']}"
        stat_avg_likes.value = f"{int(stats['total_likes'] / (stats['total_tweets'] or 1))}"
        stat_total_retweets.value = f"{stats['total_retweets']}"
        stat_avg_sentiment.value = f"{stats['avg_sentiment']}"
        
        # Color avg sentiment accordingly
        if stats['avg_sentiment'] > 0.1:
            stat_avg_sentiment.color = ft.Colors.GREEN_400
        elif stats['avg_sentiment'] < -0.1:
            stat_avg_sentiment.color = ft.Colors.RED_400
        else:
            stat_avg_sentiment.color = ft.Colors.GREY_400
            
        # 1. Update Sentiment Pie Chart
        sent_summary = db.get_sentiment_summary()
        total_sent = sum(sent_summary.values())
        
        if total_sent > 0:
            pos_p = (sent_summary['Positive'] / total_sent) * 100
            neu_p = (sent_summary['Neutral'] / total_sent) * 100
            neg_p = (sent_summary['Negative'] / total_sent) * 100
            
            pie = fch.PieChart(
                sections=[
                    fch.PieChartSection(pos_p, title=f"{pos_p:.0f}%", color=ft.Colors.GREEN_600, radius=55, title_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                    fch.PieChartSection(neu_p, title=f"{neu_p:.0f}%", color=ft.Colors.GREY_600, radius=55, title_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                    fch.PieChartSection(neg_p, title=f"{neg_p:.0f}%", color=ft.Colors.RED_600, radius=55, title_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                ],
                sections_space=3,
                center_space_radius=40,
                expand=True
            )
            
            legend = ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
                controls=[
                    ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.GREEN_600, border_radius=3), ft.Text("Olumlu", size=11, color=ft.Colors.GREY_300)]),
                    ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.GREY_600, border_radius=3), ft.Text("Nötr", size=11, color=ft.Colors.GREY_300)]),
                    ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.RED_600, border_radius=3), ft.Text("Olumsuz", size=11, color=ft.Colors.GREY_300)]),
                ]
            )
            
            sentiment_chart_container.content = ft.Column(
                controls=[
                    ft.Container(content=pie, expand=True, padding=10),
                    legend
                ],
                expand=True
            )
        else:
            sentiment_chart_container.content = ft.Text("Duygu analizi verisi yok", color=ft.Colors.GREY_500, italic=True)
            
        # 2. Update Line Chart (Tweets Over Time)
        over_time = db.get_tweets_over_time()
        if over_time:
            data_points = []
            bottom_labels = []
            for idx, (date_str, count) in enumerate(over_time):
                data_points.append(fch.LineChartDataPoint(idx, count))
                
                # Format month string (e.g. 2026-07 -> Tem '26)
                try:
                    parts = date_str.split("-")
                    year_short = parts[0][2:]
                    month_map = {"01":"Oca", "02":"Şub", "03":"Mar", "04":"Nis", "05":"May", "06":"Haz", "07":"Tem", "08":"Ağu", "09":"Eyl", "10":"Eki", "11":"Kas", "12":"Ara"}
                    short_date = f"{month_map.get(parts[1], '')} '{year_short}"
                except:
                    short_date = date_str
                    
                # Limit date labels to prevent overlap
                if len(over_time) <= 7 or idx % (len(over_time) // 5 or 1) == 0:
                    bottom_labels.append(fch.ChartAxisLabel(value=idx, label=ft.Text(short_date, size=9, color=ft.Colors.GREY_400)))
                    
            left_axis = fch.ChartAxis(
                title=ft.Text("Tweet Sayısı", size=11, color=ft.Colors.GREY_400),
                show_labels=True,
                label_size=50
            )
            
            bottom_axis = fch.ChartAxis(
                title=ft.Text("Tarih", size=11, color=ft.Colors.GREY_400),
                show_labels=True,
                labels=bottom_labels,
                label_size=20
            )
                
            line_chart_container.content = fch.LineChart(
                data_series=[
                    fch.LineChartData(
                        points=data_points,
                        color=ft.Colors.CYAN_400,
                        stroke_width=3,
                        curved=True,
                        prevent_curve_over_shooting=True
                    )
                ],
                border=ft.Border(
                    bottom=ft.BorderSide(1, ft.Colors.GREY_700),
                    left=ft.BorderSide(1, ft.Colors.GREY_700)
                ),
                horizontal_grid_lines=fch.ChartGridLines(color="#22ffffff", width=1, dash_pattern=[3, 3]),
                vertical_grid_lines=fch.ChartGridLines(color="#22ffffff", width=1, dash_pattern=[3, 3]),
                left_axis=left_axis,
                bottom_axis=bottom_axis,
                expand=True,
            )
        else:
            line_chart_container.content = ft.Text("Zaman serisi verisi yok", color=ft.Colors.GREY_500, italic=True)
            
        # 3. Update Keyword Bar Chart
        kw_summary = db.get_keyword_summary()
        if kw_summary:
            bar_groups = []
            bottom_labels = []
            
            # Palette of colors for different bars
            COLORS = [
                ft.Colors.BLUE_400,
                ft.Colors.AMBER_400,
                ft.Colors.TEAL_400,
                ft.Colors.PINK_400,
                ft.Colors.PURPLE_400,
                ft.Colors.RED_400,
                ft.Colors.GREEN_400,
                ft.Colors.INDIGO_400,
                ft.Colors.ORANGE_400,
                ft.Colors.CYAN_400
            ]
            
            top_keywords = list(kw_summary.items())[:10]
            for idx, (kw, count) in enumerate(top_keywords):
                color = COLORS[idx % len(COLORS)]
                bar_groups.append(
                    fch.BarChartGroup(
                        x=idx,
                        rods=[
                            fch.BarChartRod(
                                from_y=0,
                                to_y=count,
                                color=color,
                                width=18,
                                border_radius=4,
                            )
                        ]
                    )
                )
                bottom_labels.append(fch.ChartAxisLabel(value=idx, label=ft.Text(kw, size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400)))
            
            left_axis = fch.ChartAxis(
                title=ft.Text("Tweet Sayısı", size=11, color=ft.Colors.GREY_400),
                show_labels=True,
                label_size=50
            )
            
            bottom_axis = fch.ChartAxis(
                show_labels=True,
                labels=bottom_labels,
                label_size=25
            )
            
            keyword_chart_container.content = fch.BarChart(
                groups=bar_groups,
                border=ft.Border(
                    bottom=ft.BorderSide(1, ft.Colors.GREY_700),
                    left=ft.BorderSide(1, ft.Colors.GREY_700)
                ),
                horizontal_grid_lines=fch.ChartGridLines(color="#22ffffff", width=1, dash_pattern=[3, 3]),
                left_axis=left_axis,
                bottom_axis=bottom_axis,
                expand=True
            )
        else:
            keyword_chart_container.content = ft.Text("Anahtar kelime verisi yok", color=ft.Colors.GREY_500, italic=True)
            
        page.update()

    # Helper: Refresh Data Browser Table
    def refresh_data_browser():
        selected_kw = filter_keyword_dropdown.value
        if selected_kw == "Tümü":
            selected_kw = None
            
        # Get data from database
        tweets = db.get_filtered_tweets(keyword=selected_kw)
        
        # Populate Dropdown filter list with all active keywords in DB
        kw_summary = db.get_keyword_summary()
        options = [ft.dropdown.Option("Tümü")] + [ft.dropdown.Option(kw) for kw in kw_summary.keys()]
        filter_keyword_dropdown.options = options
        if not filter_keyword_dropdown.value:
            filter_keyword_dropdown.value = "Tümü"
            
        # Populate Table Rows
        rows = []
        for t in tweets:
            # Shorten tweet text for presentation
            short_text = t['text'][:60] + "..." if len(t['text']) > 60 else t['text']
            
            # Sentiment Badge
            lbl = t['sentiment_label']
            badge_color = ft.Colors.GREEN_400 if lbl == "Positive" else (ft.Colors.RED_400 if lbl == "Negative" else ft.Colors.GREY_500)
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(t['created_at'])),
                        ft.DataCell(ft.Text(t['author_handle'], color=ft.Colors.CYAN_200)),
                        ft.DataCell(
                            ft.Text(short_text),
                            on_tap=lambda _, text=t['text']: show_tweet_modal(text, t['author_name'], t['author_handle'])
                        ),
                        ft.DataCell(ft.Text(str(t['likes']))),
                        ft.DataCell(ft.Text(str(t['retweets']))),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(lbl, size=11, color=ft.Colors.BLACK, weight=ft.FontWeight.BOLD),
                                bgcolor=badge_color,
                                padding=ft.Padding.all(5),
                                border_radius=4,
                            )
                        ),
                    ]
                )
            )
            
        tweets_table.rows = rows
        page.update()

    def show_tweet_modal(text, author, handle):
        def close_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"{author} ({handle})"),
            content=ft.Text(text, size=16),
            actions=[
                ft.TextButton("Kapat", on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # Search & Scraping Tracking logic (Threaded)
    def start_tracking_thread(keywords, limit, start_date, end_date, client):
        nonlocal is_tracking
        is_tracking = True
        
        progress_bar.visible = True
        progress_bar.value = None # Indeterminate spinner
        page.update()
        
        all_tweets_fetched = []
        
        try:
            for idx, kw in enumerate(keywords):
                kw = kw.strip()
                if not kw:
                    continue
                    
                update_log(f"🔎 '{kw}' kelimesi aranıyor...")
                
                # Fetch callback to update status bar (throttled to 100ms)
                last_update = [0.0]
                def on_progress(current, total, msg):
                    now_time = time.time()
                    if current == total or (now_time - last_update[0]) > 0.1:
                        progress_text.value = f"[{kw}] {msg}"
                        progress_bar.value = current / total
                        page.update()
                        last_update[0] = now_time
                    
                # Search using the selected client mode
                tweets = client.search_tweets(
                    keyword=kw,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    progress_callback=on_progress
                )
                
                # Insert into DB
                inserted = db.insert_tweets(tweets)
                all_tweets_fetched.extend(tweets)
                
                update_log(f"✅ '{kw}': {len(tweets)} tweet çekildi, {inserted} yeni kayıt veritabanına yazıldı.")
                
            update_log("🎉 Arama işlemi başarıyla tamamlandı!")
            
        except Exception as ex:
            update_log(f"❌ Hata oluştu: {str(ex)}")
            
        # Complete
        is_tracking = False
        progress_bar.visible = False
        progress_text.value = "Tamamlandı"
        
        # Refresh visuals
        refresh_dashboard()
        refresh_data_browser()
        page.update()

    def start_tracking_click(e):
        if is_tracking:
            show_toast("Lütfen mevcut aramanın bitmesini bekleyin.")
            return
            
        kw_input = keywords_field.value
        if not kw_input:
            show_toast("Lütfen en az bir anahtar kelime girin.")
            return
            
        keywords = kw_input.split(",")
        limit = None
        
        start_date = start_date_field.value or None
        end_date = end_date_field.value or None
        
        # Validate date formats if entered
        for d in [start_date, end_date]:
            if d:
                try:
                    datetime.strptime(d, "%Y-%m-%d")
                except ValueError:
                    show_toast("Hatalı tarih formatı! YYYY-MM-DD olmalı.")
                    return
                    
        # Client setup
        client = TwitterClient(
            mode=settings.get("mode", "twikit"),
            api_key=settings.get("api_key"),
            api_secret=settings.get("api_secret"),
            access_token=settings.get("access_token"),
            access_token_secret=settings.get("access_token_secret"),
            bearer_token=settings.get("bearer_token"),
            twikit_username=settings.get("twikit_username"),
            twikit_password=settings.get("twikit_password"),
            twikit_email=settings.get("twikit_email")
        )
        
        # Start background search
        threading.Thread(
            target=start_tracking_thread,
            args=(keywords, limit, start_date, end_date, client),
            daemon=True
        ).start()

    def update_log(message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_list_view.controls.append(
            ft.Row(
                controls=[
                    ft.Text(f"[{timestamp}]", color=ft.Colors.GREY_500, size=12),
                    ft.Text(message, size=13)
                ]
            )
        )
        page.update()

    # Clear all data helper
    def clear_all_data(e):
        def confirm_clear(ev):
            db.clear_database()
            refresh_dashboard()
            refresh_data_browser()
            confirm_dialog.open = False
            show_toast("Tüm veritabanı temizlendi.")
            
        def cancel_clear(ev):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Veritabanını Temizle"),
            content=ft.Text("Tüm kaydedilmiş tweet verileri silinecektir. Emin misiniz?"),
            actions=[
                ft.TextButton("İptal", on_click=cancel_clear),
                ft.TextButton("Evet, Sil", on_click=confirm_clear, style=ft.ButtonStyle(color=ft.Colors.RED_400))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    # Excel Export Helper
    def export_data_click(e):
        selected_kw = filter_keyword_dropdown.value
        if selected_kw == "Tümü":
            selected_kw = None
            
        tweets = db.get_filtered_tweets(keyword=selected_kw)
        if not tweets:
            show_toast("Dışa aktarılacak veri bulunamadı.")
            return
            
        df = pd.DataFrame(tweets)
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
            
        filename = f"tweets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            df.to_excel(filename, index=False)
            show_toast(f"Veriler başarıyla aktarıldı: {filename}")
        except Exception as ex:
            show_toast(f"Dışa aktarma hatası: {str(ex)}")

    # UI Controls for search tab
    keywords_field = ft.TextField(
        label="Anahtar Kelimeler (Virgülle ayırın)",
        hint_text="Örn: yapay zeka, futbol, ekonomi",
        expand=True
    )

    start_date_field = ft.TextField(
        label="Başlangıç Tarihi",
        hint_text="YYYY-MM-DD",
        value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        width=150
    )
    end_date_field = ft.TextField(
        label="Bitiş Tarihi",
        hint_text="YYYY-MM-DD",
        value=datetime.now().strftime("%Y-%m-%d"),
        width=150
    )
    
    # Assembly: Tabs & Layouts
    dashboard_view = ft.Column(
        controls=[
            ft.Text("Gösterge Paneli & İstatistikler", size=22, weight=ft.FontWeight.BOLD),
            ft.Row(
                spacing=20,
                controls=[
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Toplam Tweet", size=14, color=ft.Colors.GREY_400),
                                    stat_total_tweets
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            padding=20,
                            width=220,
                            height=120,
                        ),
                        elevation=3
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Ortalama Beğeni", size=14, color=ft.Colors.GREY_400),
                                    stat_avg_likes
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            padding=20,
                            width=220,
                            height=120,
                        ),
                        elevation=3
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Toplam Retweet", size=14, color=ft.Colors.GREY_400),
                                    stat_total_retweets
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            padding=20,
                            width=220,
                            height=120,
                        ),
                        elevation=3
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Ortalama Duygu Skoru", size=14, color=ft.Colors.GREY_400),
                                    stat_avg_sentiment
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            padding=20,
                            width=220,
                            height=120,
                        ),
                        elevation=3
                    )
                ]
            ),
            ft.Divider(height=20, color=ft.Colors.GREY_700),
            ft.Row(
                expand=True,
                controls=[
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Duygu Dağılımı", size=16, weight=ft.FontWeight.BOLD),
                                    sentiment_chart_container
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True
                            ),
                            padding=15,
                            expand=True
                        ),
                        expand=1
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Zamansal Tweet Sayısı", size=16, weight=ft.FontWeight.BOLD),
                                    line_chart_container
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True
                            ),
                            padding=15,
                            expand=True
                        ),
                        expand=1
                    ),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Anahtar Kelime Kıyaslaması", size=16, weight=ft.FontWeight.BOLD),
                                    keyword_chart_container
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True
                            ),
                            padding=15,
                            expand=True
                        ),
                        expand=1
                    )
                ]
            )
        ],
        expand=True
    )
    
    search_view = ft.Column(
        controls=[
            ft.Text("Tweet Arama ve Veri Çekme", size=22, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    keywords_field
                ],
                spacing=15
            ),
            ft.Row(
                controls=[
                    start_date_field,
                    end_date_field,
                    ft.ElevatedButton(
                        "Aramayı Başlat", 
                        icon=ft.Icons.SEARCH, 
                        on_click=start_tracking_click,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.CYAN_600,
                            color=ft.Colors.WHITE,
                            padding=15
                        )
                    ),
                ],
                spacing=15
            ),
            progress_bar,
            progress_text,
            ft.Divider(height=20, color=ft.Colors.GREY_700),
            ft.Text("İşlem Logları", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=log_list_view,
                bgcolor=ft.Colors.BLACK26,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                border_radius=8,
                padding=10,
                expand=True
            )
        ],
        expand=True
    )
    
    data_browser_view = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("Kayıtlı Tweetler Veri Tabanı", size=22, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            filter_keyword_dropdown,
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Yenile",
                                on_click=lambda e: refresh_data_browser()
                            ),
                            ft.ElevatedButton(
                                "Excel'e Aktar",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=export_data_click,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                            ),
                            ft.ElevatedButton(
                                "Veritabanını Temizle",
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=clear_all_data,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE)
                            )
                        ]
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(height=10, color=ft.Colors.GREY_700),
            # Table Scroll Container
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[tweets_table],
                            scroll=ft.ScrollMode.ALWAYS,
                        )
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True
                ),
                bgcolor=ft.Colors.BLACK12,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                border_radius=8,
                expand=True,
                padding=10
            )
        ],
        expand=True
    )
    
    settings_view = ft.Column(
        controls=[
            ft.Text("Sistem & API Ayarları", size=22, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color=ft.Colors.GREY_700),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            api_mode_dropdown,
                            ft.Text(
                                "• Resmi API Modu: Resmi Twitter developer hesabınızın Bearer Token bilgileriyle veri çeker (Ücretlidir).",
                                size=12,
                                color=ft.Colors.GREY_400
                            ),
                            ft.Text(
                                "• Twikit Giriş Modu: X (Twitter) kullanıcı adı ve şifrenizle giriş yaparak arama sonuçlarını çeker (Ücretsiz & Canlı).",
                                size=12,
                                color=ft.Colors.GREY_400
                            ),
                        ]
                    ),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            api_fields_container,
                            twikit_fields_container,
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "Ayarları Kaydet",
                                icon=ft.Icons.SAVE,
                                on_click=save_settings_click,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
                            )
                        ]
                    ),
                    padding=15
                )
            )
        ],
        expand=True
    )
    
    # Navigation and View Switching
    def tab_changed(e):
        idx = e.control.selected_index
        # Hide all views
        dashboard_container.visible = (idx == 0)
        search_container.visible = (idx == 1)
        data_browser_container.visible = (idx == 2)
        settings_container.visible = (idx == 3)
        
        # On click, refresh views dynamically
        if idx == 0:
            refresh_dashboard()
        elif idx == 2:
            refresh_data_browser()
            
        page.update()

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Gösterge Paneli"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.TRACK_CHANGES_OUTLINED,
                selected_icon=ft.Icons.TRACK_CHANGES,
                label="Tweet Çek"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.STORAGE_OUTLINED,
                selected_icon=ft.Icons.STORAGE,
                label="Veri Havuzu"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Ayarlar"
            )
        ],
        on_change=tab_changed,
        bgcolor=ft.Colors.BLACK38
    )
    
    # Wrap views in visibility containers
    dashboard_container = ft.Container(content=dashboard_view, expand=True, visible=True)
    search_container = ft.Container(content=search_view, expand=True, visible=False)
    data_browser_container = ft.Container(content=data_browser_view, expand=True, visible=False)
    settings_container = ft.Container(content=settings_view, expand=True, visible=False)
    
    # Top-level Page Layout
    page.add(
        ft.Row(
            controls=[
                nav_rail,
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            dashboard_container,
                            search_container,
                            data_browser_container,
                            settings_container
                        ],
                        expand=True
                    ),
                    expand=True,
                    padding=20
                )
            ],
            expand=True
        )
    )
    
    # Initial load data
    refresh_dashboard()
    refresh_data_browser()

if __name__ == "__main__":
    ft.app(target=main)
