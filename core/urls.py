from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import api_views
from .forms import EmailOrMobileAuthenticationForm

urlpatterns = [
    path('search-instruments/', views.search_instruments, name='search_instruments'),
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('register/send-otp/', views.send_signup_otp, name='send_signup_otp'),
    path('register/verify-otp/', views.verify_signup_otp, name='verify_signup_otp'),
    path('upload/portfolio/', views.upload_portfolio, name='upload_portfolio'),
    path('export/portfolio/', views.export_portfolio, name='export_portfolio'),
    path('portfolio/add-manual/', views.add_portfolio_item, name='add_portfolio_item'),
    path('portfolio/sell-manual/', views.sell_portfolio_item, name='sell_portfolio_item'),
    path('portfolio/upload/', views.upload_portfolio, name='upload_portfolio'),
    path('portfolio/add-cost/', views.upload_portfolio, name='add_folio_cost'), # Mapping to upload for now
    path('watchlist/', views.watchlist, name='watchlist'),
    path('watchlist/add/', views.add_to_watchlist_api, name='add_to_watchlist_api'),
    path('watchlist/remove/', views.remove_from_watchlist_api, name='remove_from_watchlist_api'),

    path('upload/pnl/', views.upload_pnl, name='upload_pnl'),
    path('upload/rpnl/', views.upload_rpnl, name='upload_rpnl'),
    path('portfolio/edit/<int:pk>/', views.edit_portfolio_item, name='edit_portfolio_item'),
    path('portfolio/delete/<int:pk>/', views.delete_portfolio_item, name='delete_portfolio_item'),
    path('portfolio/buy/', views.buy_stock, name='buy_stock'),
    path('portfolio/sell/', views.sell_stock, name='sell_stock'),
    path('portfolio/sell-lot/', views.sell_specific_lot, name='sell_specific_lot'),
    
    # Custom Login View
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=EmailOrMobileAuthenticationForm), name='login'),
    path('accounts/google/one-tap/', views.google_one_tap_login, name='google_one_tap_login'),
    path('strategy/', views.strategy, name='strategy'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/link-family/', views.link_family_id, name='link_family_id'),
    path('profile/verify-family/', views.verify_family_otp, name='verify_family_otp'),
    path('profile/unlink-family/<int:pk>/', views.unlink_family, name='unlink_family'),
    path('profile/request-reset/', views.request_reset_otp, name='request_reset_otp'),
    path('profile/verify-reset/', views.verify_reset_otp, name='verify_reset_otp'),
    path('mf-guide/', views.mf_guide, name='mf_guide'),
    path('mf-dashboard/', views.mf_dashboard, name='mf_dashboard'),
    path('mf-detail/<int:pk>/', views.mf_detail, name='mf_detail'),
    path('mf-portfolio/add/', views.add_mf_portfolio, name='add_mf_portfolio'),
    path('mf-portfolio/sell/<int:pk>/', views.sell_mf_portfolio, name='sell_mf_portfolio'),
    path('mf-portfolio/delete/<int:pk>/', views.delete_mf_portfolio, name='delete_mf_portfolio'),
    path('mf-transactions/', views.mf_transaction_history, name='mf_transaction_history'),
    path('mf-portfolio/refresh/', views.refresh_mf_navs, name='refresh_mf_navs'),
    
    # Coin (Crypto) URLs
    path('coin/', views.coin_dashboard, name='coin_dashboard'),
    path('coin/detail/<int:pk>/', views.coin_detail, name='coin_detail'),
    path('coin/add/', views.add_coin, name='add_coin'),
    path('coin/sell/<int:pk>/', views.sell_coin, name='sell_coin'),
    path('coin/delete/<int:pk>/', views.delete_coin_portfolio, name='delete_coin_portfolio'),
    path('coin/transactions/', views.coin_transaction_history, name='coin_transaction_history'),
    path('coin/refresh/', views.refresh_coin_prices, name='refresh_coin_prices'),
    
    # NPS URLs
    path('nps/', views.nps_dashboard, name='nps_dashboard'),
    path('nps/detail/<int:pk>/', views.nps_detail, name='nps_detail'),
    path('nps/add/', views.add_nps, name='add_nps'),
    path('nps/sell/<int:pk>/', views.sell_nps, name='sell_nps'),
    path('nps/delete/<int:pk>/', views.delete_nps_portfolio, name='delete_nps_portfolio'),
    path('nps/transactions/', views.nps_transaction_history, name='nps_transaction_history'),
    path('nps/refresh/', views.refresh_nps_navs, name='refresh_nps_navs'),
    
    # FD / Fixed Assets URLs
    path('fd/', views.fd_dashboard, name='fd_dashboard'),
    path('fd/add/', views.add_fd, name='add_fd'),
    path('fd/delete/<int:pk>/', views.delete_fd, name='delete_fd'),
    
    # Other Assets URLs
    path('other-assets/', views.other_assets_dashboard, name='other_assets_dashboard'),
    path('other-assets/add/', views.add_other_asset, name='add_other_asset'),
    path('other-assets/edit/<int:pk>/', views.edit_other_asset, name='edit_other_asset'),
    path('other-assets/delete/<int:pk>/', views.delete_other_asset, name='delete_other_asset'),
    
    # Loan Module URLs
    path('loan/', views.loan_dashboard, name='loan_dashboard'),
    path('loan/add/', views.add_loan, name='add_loan'),
    path('loan/edit/<int:pk>/', views.edit_loan, name='edit_loan'),
    path('loan/delete/<int:pk>/', views.delete_loan, name='delete_loan'),
    path('loan/detail/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loan/payment/<int:pk>/', views.add_loan_payment, name='add_loan_payment'),
    
    path('portfolio/', views.portfolio, name='portfolio'),
    path('etf-guide/', views.etf_guide, name='etf_guide'),
    path('nps-guide/', views.nps_guide, name='nps_guide'),
    path('stock-guide/', views.stock_guide, name='stock_guide'),
    path('education/', views.education_hub, name='education_hub'),
    path('education/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('education/<slug:slug>/comment/', views.add_blog_comment, name='add_blog_comment'),
    path('ipo/', views.ipo_list, name='ipo'),
    path('aboutproject/', views.about_project, name='about_project'),
    # Transactions and Lots
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('transactions/save-fy-data/', views.save_fy_data, name='save_fy_data'),
    path('transactions/toggle-fy-lock/', views.toggle_fy_lock, name='toggle_fy_lock'),
    path('transactions/delete-fy-data/', views.delete_fy_data, name='delete_fy_data'),
    path('portfolio/lots/<int:instrument_id>/', views.lot_breakdown, name='lot_breakdown'),
    path('portfolio/lot/edit/<int:pk>/', views.edit_lot, name='edit_lot'),
    path('portfolio/lot/delete/<int:pk>/', views.delete_lot, name='delete_lot'),

    # Forgot Password Flow
    path('accounts/password_change/forgot/', views.forgot_password_session, name='forgot_password_session'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Internal Sync API
    path('api/sync-data/', views.sync_data_api, name='sync_data_api'),
    path('api/portfolio-history/', views.portfolio_history_api, name='portfolio_history_api'),
    path('auto-migrate/', views.auto_migrate, name='auto_migrate'),
    path('api/mf-suggestions/', views.mf_suggestions_api, name='mf_suggestions_api'),
    path('api/nps-suggestions/', views.nps_suggestions_api, name='nps_suggestions_api'),
    path('api/index-data/', views.index_data_api, name='index_data_api'),
    path('api/stock-price/', views.stock_price_api, name='stock_price_api'),
    path('api/stock-suggestions/', views.stock_suggestions_api, name='stock_suggestions_api'),
    path('api/stock-history/', views.stock_history_api, name='stock_history_api'),
    path('api/coin-price/', views.coin_price_api, name='coin_price_api'),
    path('api/coin-suggestions/', views.coin_suggestions_api, name='coin_suggestions_api'),
    path('api/backtest-strategy/', views.backtest_strategy_api, name='backtest_strategy_api'),
    
    # Mobile App API
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/portfolio/', api_views.api_portfolio, name='api_portfolio'),
    path('api/add-transaction/', api_views.api_add_transaction, name='api_add_transaction'),
    
    path('.well-known/assetlinks.json', views.assetlinks_json, name='assetlinks_json'),
    path('chatbot-response/', views.chatbot_response, name='chatbot_response'),
    path('api/toggle-hidden-signal/', views.toggle_hidden_signal, name='toggle_hidden_signal'),
    path('api/report-missing-instrument/', views.report_missing_instrument, name='report_missing_instrument'),
    path('feedback/', views.submit_review, name='feedback'),
    path('stock-news/', views.stock_news_list, name='stock_news'),
    path('calc/', views.wealth_calculators, name='wealth_calculators'),
    path('api/tax-calculator/', views.tax_calculator_api, name='tax_calculator_api'),
    path('calc/download-report/', views.download_tax_report, name='download_tax_report'),
    path('calc/api/login/', views.ajax_login_api, name='ajax_login_api'),
    path('calc/api/save/', views.save_calculation_api, name='save_calculation_api'),
    path('calc/api/list/', views.saved_calculations_list_api, name='saved_calculations_list_api'),
    path('calc/api/delete/<int:pk>/', views.delete_calculation_api, name='delete_calculation_api'),
    path('calc/api/toggle-favorite/<int:pk>/', views.toggle_favorite_calculation_api, name='toggle_favorite_calculation_api'),
    path('calc/api/duplicate/<int:pk>/', views.duplicate_calculation_api, name='duplicate_calculation_api'),
    path('accounts/update-theme/', views.update_theme_preference, name='update_theme_preference'),
    path('cashflow/', views.cashflow_dashboard, name='cashflow_dashboard'),
    path('cashflow/add/', views.add_cashflow_entry, name='add_cashflow_entry'),
    path('cashflow/delete/<int:pk>/', views.delete_cashflow_entry, name='delete_cashflow_entry'),
    path('cashflow/export/excel/', views.export_cashflow_excel, name='export_cashflow_excel'),
    path('cashflow/export/pdf/', views.export_cashflow_pdf, name='export_cashflow_pdf'),
]

