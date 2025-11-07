from django.shortcuts import render

def main_menu(request):
    return render(request, 'main_menu.html')