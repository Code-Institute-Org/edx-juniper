import json

from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import User

from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from xmodule.modulestore.django import modulestore
from lms.djangoapps.courseware.models import StudentModule, StudentModuleHistory
from capa.correctmap import CorrectMap


class Tag(models.Model):

    name = models.CharField(max_length=20)
    sort_key = models.IntegerField()

    class Meta:
        ordering = ('sort_key',)

    def __str__(self):
        return self.name


class Challenge(models.Model):
    """
    This model is used to map the challenges to the assignments in repl.it.
    Because our challenges are all created outside of our LMS, we have no
    internal record of them.

    This model will allow us to store the name of the repl.it assignment 
    and the locator for the block that the iframe was added to.

    When a student submits a challenge in repl.it, repl.it will send
    metadata about the challenge to our webhook. Our webhook handler will
    parse the data, extract the name of the assignment and use that
    assignment name to lookup the location of the challenge block.

    This will allow us to update the StudentModule with the correct
    block location, thus tying the external assignments to our own
    internal `xblock` system.
    """

    LEVEL = (
        ('Required', 'Required'),
        ('Bonus', 'Bonus'),
        ('Optional', 'Optional'),
    )

    name = models.CharField(max_length=120, blank=False, null=False)
    block_locator = models.CharField(max_length=120, blank=False, null=False)
    tags = models.ManyToManyField(Tag, blank=False, null=False)
    level = models.CharField(max_length=50, choices=LEVEL, blank=False, null=False)

    @property
    def get_course_and_block_locators(self):
        """
        Parse the `block_locator` value to extract the course and block
        ids, and then use this information to get the course and block
        locators.
        """
        course_key_partition, _, block_id_partition = str(
            self.block_locator).replace("block-v1:", "").replace(
                "+type@problem+block", "").partition("@")
        block_type = 'problem'
        course_locator = CourseLocator(*course_key_partition.split('+'))
        block_locator = BlockUsageLocator(
            course_locator, block_type, block_id_partition)
        return course_locator, block_locator
    
    @property
    def get_course_key_and_block_location(self):
        course_locator, block_locator = self.get_course_and_block_locators
        course_key = modulestore().get_course(
            course_locator).location.course_key
        block_location = modulestore().get_item(block_locator).location

        return course_key, block_location
    
    def __str__(self):
        return "%s -> %s" % (self.name, self.block_locator)


class ChallengeSubmission(models.Model):
    """
    The `ChallengeSubmission` model will store all of the data regarding
    the student's attempt to answer the challenge.

    This data is mostly used for internal information of students'
    challenge attempts.
    
    We'll use this data to determine a student's ability.

    The actual challenges are considered to be problems by Open edX'
    StudentModule table.

    When saving a record in this table, we also update the record in the
    `StudentModule` table so the data can be reflected on the student's
    Progress page.

    In addition to this, we also need to store the correct metadata in
    the `state` field in order for the conditional module to work correct.

    These behaviours are done here via some instance methods that allow us
    to parse, manipulate and update the StudentModule record.
    """

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    time_challenge_started = models.DateTimeField()
    time_challenge_submitted = models.DateTimeField()
    passed = models.BooleanField()
    attempts = models.IntegerField(default=1)

    class Meta:
        unique_together = ('student', 'challenge')

    def get_state_dict(self, module_record):
        """
        Deserialize the `state` to a dictionary so we can easily manipulate
        the `state` data.

        `module_record` is the `StudentModule` instance the we wish to read
            the state from
        
        Returns the contents of the `state` property as a dictionary
        """
        return json.loads(module_record.state)

    def get_answer_id(self, state):
        """
        Retrieve the `answer_id` from the state dict, so we can add the
        correct answer ID to the correctness mapping

        `state` is the dictionary that contains the state of the student
            activity
        
        Returns the `answer_id`
        """
        answer_id = state['input_state'].keys()[0]
        return answer_id
    
    def create_correct_map(self, answer_id):
        """
        Create a new `CorrectMap` to be added to the `state` field of the
        `StudentModule`.

        `answer_id` is simply the ID of the answer. This will be used as
            a key, with the `correct_map` as the value.

        Returns a dictionary containing the `correct_map`
        """
        cmap = CorrectMap()
        cmap.set(answer_id=answer_id, correctness='correct')
        correct_map = {"correct_map": cmap.get_dict()}
        return correct_map
    
    def update_module_state(self, module_record):
        """
        Get, parse and update the state dictionary.

        `module_record` is the `StudentModule` instance

        Returns a serialized version of the dictionary
        """
        state = self.get_state_dict(module_record)
        answer_id = self.get_answer_id(state)
        correct_map = self.create_correct_map(answer_id)
        state.update(correct_map)
        return json.dumps(state)

    def save(self, *args, **kwargs):
        """
        Save the ChallengeSubmission instance and update the relevant
        `StudentModule` instance to reflect the student's progress.
        """
        course_key, block_location = self.challenge.get_course_key_and_block_location

        grade = 1.0 if self.passed else 0

        student_activity = StudentModule.objects.get(student=self.student,
            module_state_key=block_location, course_id=course_key)
        
        student_activity.state = self.update_module_state(student_activity)
        student_activity.grade = grade
        student_activity.max_grade = 1.0

        student_activity.save()
        super(ChallengeSubmission, self).save(*args, **kwargs)
