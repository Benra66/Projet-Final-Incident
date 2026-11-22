from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from incidents.forms import IncidentWorkflowForm
from incidents.models import Incident, IncidentAuditEvent, IncidentComment

class IncidentSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = get_user_model().objects.create_user(username="alice", password="test-password-only")
        cls.bob = get_user_model().objects.create_user(username="bob", password="test-password-only")
        cls.alice_incident = Incident.objects.create(title="Alice private report", description="Alice synthetic incident details.", created_by=cls.alice)
        cls.bob_incident = Incident.objects.create(title="Bob private report", description="Bob synthetic incident details.", created_by=cls.bob)

    def test_anonymous_views_require_login(self):
        for url in [reverse("incidents:list"), reverse("incidents:create"), reverse("incidents:detail", args=[self.alice_incident.pk])]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_anonymous_cannot_create_incident(self):
        before = Incident.objects.count()
        response = self.client.post(reverse("incidents:create"), {"title": "Anonymous attempt", "description": "This should not be created."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Incident.objects.count(), before)

    def test_list_contains_only_owned_incidents(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("incidents:list"))
        self.assertContains(response, "Alice private report")
        self.assertNotContains(response, "Bob private report")
        self.assertEqual(response.context["paginator"].count, 1)

    def test_owner_can_open_incident(self):
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("incidents:detail", args=[self.alice_incident.pk])), "Alice synthetic incident details.")

    def test_other_users_incident_and_missing_incident_are_not_found(self):
        self.client.force_login(self.alice)
        for pk in [self.bob_incident.pk, 999999]:
            self.assertEqual(self.client.get(reverse("incidents:detail", args=[pk])).status_code, 404)

    def test_owner_is_bound_server_side_even_if_client_supplies_another(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("incidents:create"), {
            "title": "A newly reported issue", "description": "A synthetic issue with enough detail.",
            "created_by": self.bob.pk,
        })
        obj = Incident.objects.get(title="A newly reported issue")
        self.assertEqual(obj.created_by, self.alice)
        self.assertRedirects(response, reverse("incidents:detail", args=[obj.pk]))

    def test_short_input_is_accepted_without_a_minimum_length_rule(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("incidents:create"), {"title": "a", "description": "x"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Incident.objects.filter(title="a", description="x", created_by=self.alice).exists())

    def test_overlong_input_is_rejected_without_writing(self):
        self.client.force_login(self.alice)
        for title, description in [("x" * 2001, "Valid description text"), ("Valid title", "x" * 5001)]:
            before = Incident.objects.count()
            response = self.client.post(reverse("incidents:create"), {"title": title, "description": description})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            self.assertEqual(Incident.objects.count(), before)

    def test_script_shaped_text_is_escaped_on_list_and_detail(self):
        self.client.force_login(self.alice)
        payload = "<script>alert('lab')</script>"
        item = Incident.objects.create(title=payload, description=payload, created_by=self.alice)
        for url in [reverse("incidents:list"), reverse("incidents:detail", args=[item.pk])]:
            response = self.client.get(url)
            self.assertNotContains(response, payload)
            self.assertContains(response, "&lt;script&gt;")

    def test_sql_shaped_title_is_stored_as_data(self):
        self.client.force_login(self.alice)
        title = "' OR '1'='1"
        response = self.client.post(reverse("incidents:create"), {"title": title, "description": "A SQL-shaped title used as harmless data."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Incident.objects.get(title=title).created_by, self.alice)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_create_requires_csrf_proof(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        data = {"title": "CSRF test report", "description": "A synthetic CSRF verification record."}
        self.assertEqual(client.post(reverse("incidents:create"), data).status_code, 403)
        client.get(reverse("incidents:create"))
        token = client.cookies["incidentdesk_csrf"].value
        response = client.post(reverse("incidents:create"), {**data, "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)

    def test_cross_origin_post_is_rejected_even_with_cookie_and_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        client.get(reverse("incidents:create"))
        response = client.post(reverse("incidents:create"), {
            "title": "Origin test", "description": "A synthetic origin mismatch test.",
            "csrfmiddlewaretoken": client.cookies["incidentdesk_csrf"].value,
        }, HTTP_ORIGIN="https://attacker.invalid")
        self.assertEqual(response.status_code, 403)

    def test_private_pages_have_no_store_and_security_headers(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("incidents:list"))
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])

    def test_normal_user_cannot_enter_admin(self):
        self.client.force_login(self.alice)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.headers["Location"])

    def test_application_admin_sees_all_incidents(self):
        admin_user = get_user_model().objects.create_user(username="incident-admin", password="test-password-only", is_staff=True)
        group, _ = Group.objects.get_or_create(name="Incident administrators")
        admin_user.groups.add(group)
        group.permissions.add(
            Permission.objects.get(content_type__app_label="incidents", codename="view_all_incidents"),
            Permission.objects.get(content_type__app_label="incidents", codename="view_incident"),
            Permission.objects.get(content_type__app_label="incidents", codename="delete_incident"),
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse("incidents:list"))
        self.assertContains(response, "Alice private report")
        self.assertContains(response, "Bob private report")
        self.assertEqual(response.context["paginator"].count, 2)

    def test_reporter_cannot_delete_an_incident(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("incidents:delete", args=[self.alice_incident.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Incident.objects.filter(pk=self.alice_incident.pk).exists())

    def test_admin_delete_is_post_only_and_keeps_audit_event(self):
        admin_user = get_user_model().objects.create_user(username="delete-admin", password="test-password-only", is_staff=True)
        group, _ = Group.objects.get_or_create(name="Incident administrators")
        admin_user.groups.add(group)
        group.permissions.add(
            Permission.objects.get(content_type__app_label="incidents", codename="view_all_incidents"),
            Permission.objects.get(content_type__app_label="incidents", codename="delete_incident"),
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse("incidents:delete", args=[self.alice_incident.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("incidents:delete", args=[self.alice_incident.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Incident.objects.filter(pk=self.alice_incident.pk).exists())
        from incidents.models import IncidentAuditEvent
        event = IncidentAuditEvent.objects.get(incident_reference=self.alice_incident.reference, action="deleted")
        self.assertIsNone(event.incident)

    def test_assigned_analyst_sees_only_assigned_and_owned_incidents(self):
        analyst = get_user_model().objects.create_user(username="analyst", password="test-password-only")
        group, _ = Group.objects.get_or_create(name="Incident analysts")
        group.permissions.add(
            Permission.objects.get(content_type__app_label="incidents", codename="view_assigned_incidents"),
            Permission.objects.get(content_type__app_label="incidents", codename="view_incident"),
        )
        analyst.groups.add(group)
        self.alice_incident.assigned_to = analyst
        self.alice_incident.save()
        self.client.force_login(analyst)
        response = self.client.get(reverse("incidents:list"))
        self.assertContains(response, "Alice private report")
        self.assertNotContains(response, "Bob private report")

    def test_admin_can_assign_only_active_analysts(self):
        admin_user = get_user_model().objects.create_user(username="assign-admin", is_staff=True)
        analyst = get_user_model().objects.create_user(username="active-analyst", is_active=True)
        inactive_analyst = get_user_model().objects.create_user(username="inactive-analyst", is_active=False)
        ordinary_user = get_user_model().objects.create_user(username="ordinary-user")
        group, _ = Group.objects.get_or_create(name="Incident analysts")
        group.permissions.add(Permission.objects.get(content_type__app_label="incidents", codename="view_assigned_incidents"))
        group.user_set.add(analyst, inactive_analyst)
        admin_group, _ = Group.objects.get_or_create(name="Incident administrators")
        admin_group.permissions.add(Permission.objects.get(content_type__app_label="incidents", codename="assign_incident"))
        admin_user.groups.add(admin_group)

        form = IncidentWorkflowForm(user=admin_user)
        assigned_ids = set(form.fields["assigned_to"].queryset.values_list("pk", flat=True))
        self.assertEqual(assigned_ids, {analyst.pk})
        self.assertNotIn(ordinary_user.pk, assigned_ids)

    def test_homepage_contains_cv_and_login_link(self):
        response = self.client.get(reverse("incidents:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Benson Jean-Marc Arthur")
        self.assertContains(response, reverse("login"))

    def test_comment_is_escaped_and_audited_without_storing_body_in_metadata(self):
        self.client.force_login(self.alice)
        payload = "<script>comment()</script>"
        response = self.client.post(reverse("incidents:comment", args=[self.alice_incident.pk]), {"body": payload})
        self.assertEqual(response.status_code, 302)
        detail = self.client.get(reverse("incidents:detail", args=[self.alice_incident.pk]))
        self.assertNotContains(detail, payload)
        self.assertContains(detail, "&lt;script&gt;")
        comment = IncidentComment.objects.get(body=payload)
        event = IncidentAuditEvent.objects.get(action="commented", actor=self.alice)
        self.assertEqual(event.metadata, {"comment_id": comment.pk})

    def test_status_transitions_are_validated(self):
        incident = Incident.objects.get(pk=self.alice_incident.pk)
        triage = IncidentWorkflowForm(data={"status": "in_progress", "severity": "high"}, instance=incident)
        self.assertTrue(triage.is_valid(), triage.errors)
        triage.save()
        reopen = IncidentWorkflowForm(data={"status": "open", "severity": "high"}, instance=incident)
        self.assertFalse(reopen.is_valid())
        self.assertIn("status", reopen.errors)

    def test_commenter_cannot_comment_on_another_reporters_incident(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("incidents:comment", args=[self.bob_incident.pk]), {"body": "Not authorized"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(IncidentComment.objects.filter(body="Not authorized").exists())

    @override_settings(DEBUG=True)
    def test_seed_is_idempotent_and_creates_no_accounts(self):
        for _ in range(2):
            call_command("seed_incidents", username="alice", stdout=StringIO())
        self.assertEqual(self.alice.incidents.count(), 3)
        self.assertEqual(get_user_model().objects.count(), 2)

    @override_settings(DEBUG=False)
    def test_seed_refuses_production(self):
        with self.assertRaises(CommandError):
            call_command("seed_incidents", username="alice", stdout=StringIO())

class SessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reporter", password="test-password-only")

    def test_valid_login_and_safe_next_redirect(self):
        response = self.client.post(reverse("login"), {"username": "reporter", "password": "test-password-only", "next": "https://attacker.invalid/"})
        self.assertRedirects(response, reverse("incidents:list"))

    def test_invalid_login_is_generic(self):
        response = self.client.post(reverse("login"), {"username": "reporter", "password": "wrong"})
        self.assertContains(response, "Check your username and password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_repeated_invalid_logins_are_throttled(self):
        responses = [
            self.client.post(reverse("login"), {"username": "reporter", "password": "wrong"})
            for _ in range(6)
        ]
        self.assertTrue(any(response.status_code == 429 for response in responses))

    def test_login_rotates_existing_session_key(self):
        session = self.client.session
        session["anonymous_note"] = "synthetic"
        session.save()
        old = session.session_key
        response = self.client.post(reverse("login"), {"username": "reporter", "password": "test-password-only"})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(self.client.session.session_key, old)
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter(session_key=old).exists())

    def test_logout_requires_post_and_csrf_then_invalidates_session(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        client.get(reverse("incidents:list"))
        old = client.session.session_key
        response = client.post(reverse("logout"), {"csrfmiddlewaretoken": client.cookies["incidentdesk_csrf"].value})
        self.assertEqual(response.status_code, 302)
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter(session_key=old).exists())
        self.assertNotIn("_auth_user_id", client.session)
