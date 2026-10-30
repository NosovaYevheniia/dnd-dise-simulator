from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator


class Character(models.Model):
    ABILITY_SCORE_VALIDATORS = [
        MinValueValidator(3),
        MaxValueValidator(18),
    ]

    name = models.CharField(max_length=100)
    race = models.CharField(max_length=50)
    character_class = models.CharField(max_length=50)
    level = models.PositiveIntegerField(default=1)
    strength = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    dexterity = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    constitution = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    intelligence = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    wisdom = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    charisma = models.PositiveSmallIntegerField(
        default=10,
        validators=ABILITY_SCORE_VALIDATORS,
    )
    image = models.ImageField(
        upload_to="characters/",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name


class UserPreferences(models.Model):
    THEME_FANTASY = "fantasy"
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_FANTASY, "Fantasy"),
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default=THEME_FANTASY,
    )
    large_text = models.BooleanField(default=False)
    reduce_motion = models.BooleanField(default=False)

    def __str__(self):
        return f"Preferences for {self.user}"


class DiceRoll(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dice_rolls",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    sides = models.PositiveSmallIntegerField()
    rolls = models.JSONField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False, session_key__isnull=True)
                    | models.Q(user__isnull=True, session_key__isnull=False)
                ),
                name="dice_roll_has_one_owner",
            ),
        ]

    @property
    def quantity(self):
        return len(self.rolls)

    def __str__(self):
        return f"{self.quantity}d{self.sides}: {self.total}"
