from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Character, DiceRoll, UserPreferences


class CharacterImageUploadTests(TestCase):
    def create_image_upload(self, image_format="PNG", size=(1, 1)):
        image_data = BytesIO()
        Image.new("RGB", size, color="purple").save(
            image_data,
            format=image_format,
        )
        extension = image_format.lower()
        return SimpleUploadedFile(
            f"character.{extension}",
            image_data.getvalue(),
            content_type=f"image/{extension}",
        )

    def character_form_data(self, image):
        return {
            "name": "Test Hero",
            "race": "Elf",
            "character_class": "Ranger",
            "level": 3,
            "strength": 15,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 12,
            "wisdom": 11,
            "charisma": 10,
            "image": image,
        }

    def test_create_character_saves_and_displays_uploaded_image(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("create_character"),
                    self.character_form_data(self.create_image_upload()),
                )

                character = Character.objects.get(name="Test Hero")
                image_path = Path(media_root) / character.image.name

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["HX-Trigger"], "characterSaved")
                self.assertTrue(image_path.is_file())
                self.assertEqual(character.strength, 15)
                self.assertEqual(character.dexterity, 14)
                self.assertEqual(character.constitution, 13)
                self.assertEqual(character.intelligence, 12)
                self.assertEqual(character.wisdom, 11)
                self.assertEqual(character.charisma, 10)

                list_response = self.client.get(reverse("characters"))
                self.assertContains(
                    list_response,
                    f'<img class="character-image" src="{character.image.url}" '
                    f'alt="{character.name}">',
                    html=True,
                )

                form_response = self.client.get(
                    reverse("edit_character", args=[character.pk])
                )
                for ability in (
                    "strength",
                    "dexterity",
                    "constitution",
                    "intelligence",
                    "wisdom",
                    "charisma",
                ):
                    self.assertContains(
                        form_response,
                        f'id="id_{ability}"',
                    )
                    self.assertContains(
                        form_response,
                        f'name="{ability}"',
                    )
                    self.assertContains(
                        form_response,
                        'type="range"',
                    )
                    self.assertContains(
                        form_response,
                        'min="3" max="18"',
                    )

    def test_rejects_images_larger_than_five_megabytes(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("create_character"),
                    self.character_form_data(
                        self.create_image_upload("BMP", size=(1400, 1400))
                    ),
                )

                self.assertContains(
                    response,
                    "Image must be 5 MB or smaller.",
                )
                self.assertFalse(Character.objects.exists())

    def test_edit_character_updates_fields_and_keeps_existing_image(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                character = Character.objects.create(
                    name="Old Name",
                    race="Elf",
                    character_class="Ranger",
                    level=3,
                    image=self.create_image_upload(),
                )
                existing_image_name = character.image.name

                edit_url = reverse(
                    "edit_character",
                    args=[character.pk],
                )
                get_response = self.client.get(edit_url)

                self.assertContains(get_response, "Old Name")
                self.assertContains(get_response, "Save Changes")

                response = self.client.post(edit_url, {
                    "name": "New Name",
                    "race": "Dwarf",
                    "character_class": "Fighter",
                    "level": 5,
                    "strength": 8,
                    "dexterity": 9,
                    "constitution": 10,
                    "intelligence": 11,
                    "wisdom": 12,
                    "charisma": 13,
                })

                character.refresh_from_db()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["HX-Trigger"], "characterSaved")
                self.assertEqual(Character.objects.count(), 1)
                self.assertEqual(character.name, "New Name")
                self.assertEqual(character.race, "Dwarf")
                self.assertEqual(character.character_class, "Fighter")
                self.assertEqual(character.level, 5)
                self.assertEqual(character.image.name, existing_image_name)
                self.assertEqual(character.strength, 8)
                self.assertEqual(character.dexterity, 9)
                self.assertEqual(character.constitution, 10)
                self.assertEqual(character.intelligence, 11)
                self.assertEqual(character.wisdom, 12)
                self.assertEqual(character.charisma, 13)

    def test_create_character_rejects_scores_outside_slider_range(self):
        form_data = self.character_form_data(None)
        form_data.pop("image")
        form_data["strength"] = 19

        response = self.client.post(
            reverse("create_character"),
            form_data,
        )

        self.assertContains(response, "Ensure this value is less than or equal to 18.")
        self.assertFalse(Character.objects.exists())


class SettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="adventurer",
            password="Original!Pass2026",
        )
        self.client.force_login(self.user)
        self.settings_url = reverse("settings")

    def test_settings_requires_login(self):
        self.client.logout()

        response = self.client.get(self.settings_url)

        self.assertRedirects(
            response,
            f"{reverse('login_page')}?next={self.settings_url}",
        )

    def test_preferences_are_saved_and_applied_to_pages(self):
        response = self.client.post(self.settings_url, {
            "section": "appearance",
            "theme": UserPreferences.THEME_DARK,
            "large_text": "on",
            "reduce_motion": "on",
        })

        self.assertRedirects(response, self.settings_url)
        preferences = UserPreferences.objects.get(user=self.user)
        self.assertEqual(preferences.theme, UserPreferences.THEME_DARK)
        self.assertTrue(preferences.large_text)
        self.assertTrue(preferences.reduce_motion)

        page_response = self.client.get(reverse("dice_roller"))
        self.assertContains(page_response, 'data-theme="dark"')
        self.assertContains(page_response, 'data-large-text="true"')
        self.assertContains(page_response, 'data-reduce-motion="true"')

    def test_username_and_password_can_be_changed(self):
        username_response = self.client.post(self.settings_url, {
            "section": "username",
            "username": "new-adventurer",
        })
        self.assertRedirects(username_response, self.settings_url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new-adventurer")

        password_response = self.client.post(self.settings_url, {
            "section": "password",
            "old_password": "Original!Pass2026",
            "new_password1": "New!SecurePass2026",
            "new_password2": "New!SecurePass2026",
        })
        self.assertRedirects(password_response, self.settings_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New!SecurePass2026"))
        self.assertEqual(
            self.client.get(self.settings_url).status_code,
            200,
        )


class BaseTemplateTests(TestCase):
    def test_application_pages_share_the_base_navigation(self):
        user = get_user_model().objects.create_user(
            username="layout-user",
            password="Layout!Pass2026",
        )
        self.client.force_login(user)

        for route_name in (
            "home",
            "dice_roller",
            "characters",
            "roll_history",
            "settings",
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Main navigation"')
                self.assertContains(response, 'data-theme="fantasy"')
                self.assertContains(response, 'class="sidebar-logout-button"')
                if route_name == "home":
                    self.assertContains(
                        response,
                        'href="/static/styles.css"',
                    )
                    self.assertContains(response, 'class="home-page"')
                    self.assertContains(
                        response,
                        f'href="{reverse("characters")}"',
                    )
                    self.assertContains(response, "Create a Character")

    def test_authentication_pages_also_inherit_the_base_template(self):
        for url in (reverse("login_page"), reverse("register")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "<!DOCTYPE html>")
                self.assertContains(response, 'class="auth-page"')

    def test_sidebar_logout_redirects_to_login_page(self):
        user = get_user_model().objects.create_user(
            username="logout-user",
            password="Logout!Pass2026",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login_page"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class DiceRollHistoryTests(TestCase):
    def test_roll_is_generated_and_saved_to_anonymous_session_history(self):
        response = self.client.post(reverse("roll_dice"), {
            "sides": "20",
            "quantity": "3",
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sides"], 20)
        self.assertEqual(len(data["rolls"]), 3)
        self.assertEqual(data["total"], sum(data["rolls"]))
        self.assertTrue(all(1 <= roll <= 20 for roll in data["rolls"]))

        saved_roll = DiceRoll.objects.get(pk=data["id"])
        self.assertIsNone(saved_roll.user)
        self.assertEqual(saved_roll.session_key, self.client.session.session_key)
        self.assertEqual(saved_roll.rolls, data["rolls"])

        history_response = self.client.get(reverse("roll_history"))
        self.assertContains(history_response, "3d20")
        self.assertContains(history_response, f"Total: {data['total']}")

    def test_history_is_private_to_the_owning_session_or_user(self):
        self.client.post(reverse("roll_dice"), {
            "sides": "6",
            "quantity": "1",
        })
        other_client = self.client_class()
        other_history = other_client.get(reverse("roll_history"))
        self.assertContains(other_history, "No rolls yet")

        user = get_user_model().objects.create_user(
            username="history-owner",
            password="History!Pass2026",
        )
        self.client.force_login(user)
        self.client.post(reverse("roll_dice"), {
            "sides": "8",
            "quantity": "2",
        })

        user_rolls = DiceRoll.objects.filter(user=user)
        self.assertEqual(user_rolls.count(), 1)
        self.assertIsNone(user_rolls.get().session_key)
        self.assertContains(self.client.get(reverse("roll_history")), "2d8")

    def test_rejects_invalid_roll_parameters(self):
        for data in (
            {"sides": "5", "quantity": "1"},
            {"sides": "20", "quantity": "0"},
            {"sides": "20", "quantity": "21"},
            {"sides": "not-a-number", "quantity": "2"},
        ):
            with self.subTest(data=data):
                response = self.client.post(reverse("roll_dice"), data)
                self.assertEqual(response.status_code, 400)

        self.assertFalse(DiceRoll.objects.exists())
