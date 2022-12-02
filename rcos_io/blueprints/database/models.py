"""This module contains Peewee models that are mapped to database tables."""

import datetime
from playhouse.postgres_ext import (
    PostgresqlExtDatabase,
    Model,
    CharField,
    DateField,
    DateTimeField,
    BooleanField,
    TextField,
    ArrayField,
    IntegerField,
    ForeignKeyField,
)
from rcos_io import settings

db = PostgresqlExtDatabase(
    settings.PGDATABASE,
    user=settings.PGUSER,
    password=settings.PGPASSWORD,
    host=settings.PGHOST,
    port=settings.PGPORT,
)
"""The database instance."""


class BaseModel(Model):
    """Base model that other models should inherit from."""

    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class that defines metadata for this base class."""

        database = db


class Semester(BaseModel):
    """Represents a school semester that RCOS takes place during."""

    type = CharField(
        choices=(("spring", "Spring"), ("summer", "Summer"), ("fall", "Fall"))
    )
    start_date = DateField()
    end_date = DateField()
    is_accepting_new_projects = BooleanField(default=False)


class User(BaseModel):
    """
    Represents a person that interacts with RCOS. Can be a student, a faculty advisor,
    or non-RPI affiliated external members like IBM mentors.
    """

    is_approved = BooleanField(default=False)
    """Whether the user has been approved to access the site."""

    email = CharField(unique=True)

    secondary_email = CharField(null=True)

    is_secondary_email_verified = BooleanField(default=False)

    role = CharField(choices=(("rpi", "RPI"), ("external", "External")))

    first_name = CharField(null=True)

    last_name = CharField(null=True)

    rcs_id = CharField(unique=True, null=True)

    discord_user_id = CharField(unique=True, null=True)

    github_username = CharField(unique=True, null=True)

    graduation_year = IntegerField(null=True)

    @property
    def full_name(self):
        """
        The user's full name, taking into account either or both
        first and last names being null.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        if self.last_name:
            return self.last_name
        return "Unnamed User"

    @property
    def display_name(self):
        """The publicly displayable display name for the user."""
        if self.role == "rpi":
            name = self.full_name
            if self.graduation_year:
                name += " '" + str(self.graduation_year)[2:]
            return name
        return self.full_name

    def __str__(self) -> str:
        return f"<{self.role} user {self.email}>"


class Project(BaseModel):
    """Represents an RCOS project that may span multiple semesters."""

    is_approved = BooleanField(default=False)
    name = CharField()
    short_description = CharField()
    description_markdown = TextField()
    is_seeking_members = BooleanField(default=False)
    tags = ArrayField(CharField)
    github_repos = ArrayField(CharField)


class Enrollment(BaseModel):
    """Represents an instance of a user participating in RCOS for a particular semester."""

    semester = ForeignKeyField(Semester, backref="enrollments")
    user = ForeignKeyField(User, backref="enrollments")
    project = ForeignKeyField(Project, backref="enrollments")
    is_project_lead = BooleanField(default=False)
    is_coordinator = BooleanField(default=False)
    is_faculty_advisor = BooleanField(default=False)
    credits = IntegerField(default=0)
    is_for_pay = BooleanField(default=False)


def create_tables():
    """Executes CREATE TABLE SQL for each model to actually create the tables."""
    with db:
        db.create_tables([Semester, User, Project, Enrollment])
