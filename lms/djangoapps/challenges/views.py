import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.response import Response

from challenges.models import Challenge, ChallengeSubmission


def get_submission_or_none(student, challenge):
    try:
        submission = ChallengeSubmission.objects.get(
            student=student, challenge=challenge)
    except ChallengeSubmission.DoesNotExist:
        submission = None

    return submission


@csrf_exempt
def challenge_handler(request):
    assignment_data = json.loads(request.body.decode('utf-8'))

    student_email = assignment_data['student']['email']
    student_name = "{} {}".format(
        assignment_data['student']['first_name'],
        assignment_data['student']['last_name']
    )

    assignment_name = assignment_data['assignment']['name']
    assignment_score = assignment_data['submission']['status']
    assignment_created_timestamp = assignment_data['submission']['time_created']
    assignment_submitted_timestamp = assignment_data['submission']['time_submitted']
    assignment_passed = True if assignment_score == "complete" else False

    try:
        student = User.objects.get(email=student_email)
    except User.DoesNotExist:
        pass

    try:
        challenge = Challenge.objects.get(name=assignment_name)
    except Challenge.DoesNotExist:
        pass

    submission = get_submission_or_none(student, challenge)

    if not submission:
        submission = ChallengeSubmission(
            student=student, challenge=challenge,
            time_challenge_started=assignment_created_timestamp,
            time_challenge_submitted=assignment_submitted_timestamp,
            passed=assignment_passed
        )
    else:
        submission.passed = assignment_passed
        submission.attempts += 1

    submission.save()

    return HttpResponse(status=200)


@csrf_exempt
def has_completed_challenge(request):
    student = request.user
    block_id = request.GET.get('block_id', None)

    try:
        submission = ChallengeSubmission.objects.get(
            student=student, challenge__block_locator__contains=block_id)
        attempts = submission.attempts
    except:
        submission = False
        attempts = 0

    return JsonResponse({'submission': True if submission else False, "attempts": attempts})


