from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('add-to-cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('orders/', views.order_list, name='order_list'),

    # simple admin product management pages (web)
    path('admin/products/', views.admin_product_list, name='admin_product_list'),
    path('admin/product/add/', views.admin_product_add, name='admin_product_add'),
    path('admin/product/edit/<int:pk>/', views.admin_product_edit, name='admin_product_edit'),
    path('admin/product/delete/<int:pk>/', views.admin_product_delete, name='admin_product_delete'),

    # emali
    path('order/confirm/<int:order_id>/', views.confirm_order, name='confirm_order'),
    path('confirm_shipment/<int:order_id>/<str:code>/', views.confirm_shipment_view, name='confirm_shipment'),
    path('send_code/', views.send_code, name='send_code'),
    path('register/', views.register_view, name='register'),

    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:uid>/<str:token>/', views.reset_password_view, name='reset_password'),

    path('product/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),

    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/update/', views.update_cart_quantity, name='update_cart_quantity'),

    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/<int:pk>/update/', views.admin_order_update, name='admin_order_update'),

    path('admin/report/', views.sales_report, name='sales_report'),

    path('admin/report/export/',views.export_sales_report_csv,name='export_sales_report_csv'),

    path('account/delete/', views.delete_account_view, name='delete_account'),

]
