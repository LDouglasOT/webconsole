from django.shortcuts import render

def management_selection(request):
    return render(request, 'registration/management_selection.html')