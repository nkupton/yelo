import json
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from yelo.lib.elo_utils import play_match
from yelo.lib.http import api_error
from yelo.models import Elo, Match
from yelo.serializers import (
    EloSerializer,
    MatchSerializer,
    GroupSerializer,
    UserSerializer
)
import collections

# Create your views here.


def index(request):
    return render(request, "index.html", {
        'title': 'yelo'
    })


def profile(request, player):
    return render(request, "profile.html", {
        'title': 'yelo',
        'player': player,
        'rating_history': get_matches_by_player(player)
    })


@csrf_exempt
def record_match(request):
    if request.method != 'POST':
        return api_error('record_match must be called as a POST')

    form = json.loads(request.body.decode('utf-8'))

    if form['winner'] == form['loser']:
        return api_error(form['winner'] + ' cannot be both the winner and the loser of a match.')

    winner = User.objects.get(username=form['winner'])
    winner_elo = winner.elo.elo

    loser = User.objects.get(username=form['loser'])
    loser_elo = loser.elo.elo

    new_winner_elo, new_loser_elo = play_match(winner_elo, loser_elo)

    match = Match(
        winner=winner,
        winner_before_elo=winner_elo,
        winner_after_elo=new_winner_elo,
        loser=loser,
        loser_before_elo=loser_elo,
        loser_after_elo=new_loser_elo
    )
    match.save()

    winner.elo.elo = new_winner_elo
    winner.elo.save()

    loser.elo.elo = new_loser_elo
    loser.elo.save()

    return JsonResponse({
        'success': True
    })


@csrf_exempt
def add_player(request):
    if request.method != 'POST':
        return api_error('add_player must be called as a POST')

    form = json.loads(request.body.decode('utf-8'))

    elo = Elo(
        player=User.objects.create_user(form['name'])
    )
    elo.save()

    return JsonResponse({
        'success': True
    })


@csrf_exempt
def get_matches_by_player(player):

    user = User.objects.get(username=player)
    wins = Match.objects.filter(winner=user)
    losses = Match.objects.filter(loser=user)

    rating_history = dict()
    for win in wins:
        rating_history[win.match_date] = win.winner_after_elo
    for loss in losses:
        rating_history[loss.match_date] = loss.loser_after_elo

    sorted_rating_history = collections.OrderedDict()
    for k in sorted(rating_history.keys()):
        sorted_rating_history[k] = rating_history[k]

    #javascript wants a zero based month, what the hell?
    resp = [{'x': 'new Date(' + ','.join(str(a) for a in [date.year, date.month - 1, date.day, date.hour, date.minute, date.second]) + ')', 'y': elo} for date, elo in sorted_rating_history.items()]
    resp = JsonResponse(
        resp,
        safe=False
    )
    #Unfortunate formatting adjustments to give canvasjs what it wants
    resp = str(resp.content.decode('utf-8')).replace("\"", '')
    resp = resp.replace("Content-Type: application/json", "")
    return resp


class EloViewSet(viewsets.ModelViewSet):

    queryset = Elo.objects.all()
    serializer_class = EloSerializer
    ordering = ('-elo',)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class MatchViewSet(viewsets.ModelViewSet):

    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    ordering = ('-match_date',)
