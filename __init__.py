from __future__ import division  # Use floating point for math calculations

import math

from flask import Blueprint, session

from CTFd.models import Challenges, Solves, db, Flags, Awards, Fails
from CTFd.plugins.flags import FlagException, get_flag_class
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils.user import get_current_user, get_ip
from CTFd.utils.modes import get_model


class MultiAnswerChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "multianswer"}
    id = db.Column(None, db.ForeignKey('challenges.id'), primary_key=True)
    flagpoints = db.Column(db.Integer)
    flagcount = db.Column(db.Integer)

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.flagpoints = int(kwargs['flagpoints'])
        self.flagcount = int(kwargs['flagcount'])
        self.value = 0

    

class MultiAnswerChallenge(BaseChallenge):
    id = "multianswer"  # Unique identifier used to register challenges
    name = "multianswer"  # Name of a challenge type
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/CTFD-multi-answer/assets/create.html",
        "update": "/plugins/CTFD-multi-answer/assets/update.html",
        "view": "/plugins/CTFD-multi-answer/assets/view.html"
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/CTFD-multi-answer/assets/create.js",
        "update": "/plugins/CTFD-multi-answer/assets/update.js",
        "view": "/plugins/CTFD-multi-answer/assets/view.js"
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/CTFD-multi-answer/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "multianswer",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = MultiAnswerChallenge


    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.
        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        challengeValue = 0
        for flag in flags:
            challengeValue += challenge.flagpoints

        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challengeValue,
            "description": challenge.description,
            "flagpoints": challenge.flagpoints,
            "flagcount": challenge.flagcount,
            "connection_info": challenge.connection_info,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
        }
        return data



    @classmethod
    def attempt(cls, challenge, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.
        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        data = request.form or request.get_json()
        submission = data["submission"]
        correctAnswers = 0
        submissionArray = submission.split(',')
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                for sub in submissionArray:
                    if get_flag_class(flag.type).compare(flag, sub.strip()):
                        correctAnswers += 1               
            except FlagException as e:
                return False, str(e)
        
        if correctAnswers == 0:
            return False, "0 " + " out of " + str(len(flags)) + " Answers you submitted are correct"
        else:
            return True, str(correctAnswers) + " out of " + str(len(flags)) + " Answers you submitted are correct"

    @staticmethod
    def solve(user, team, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        correctAnswers = 0
        submissionArray = submission.split(',')
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                for sub in submissionArray:
                    if get_flag_class(flag.type).compare(flag, sub.strip()):
                        award = Awards(
                            user_id=user.id,
                            team_id=team.id if team else None,
                            name=challenge.name,
                            value=challenge.flagpoints,
                            description=sub.strip()
                        )
                        db.session.add(award)
                        db.session.commit()        
            except FlagException as e:
                return str(e)
        
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()
        
        return challenge




def load(app):
    upgrade()
    app.db.create_all()
    CHALLENGE_CLASSES["multianswer"] = MultiAnswerChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/CTFD-multi-answer/assets/"
    )