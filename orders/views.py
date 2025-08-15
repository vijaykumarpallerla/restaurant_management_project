from django.shortcuts import render


def homepage(request):
    return render(request, 'homepage.html')


def custom_404(request, exception):
    return render(request , '404.html', status=404)
