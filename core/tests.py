from django.test import TestCase, Client
from django.urls import reverse
from core.models import CustomUser, SessionPlan, Activity

class SessionPlanEditorTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test teacher user
        self.teacher = CustomUser.objects.create_user(
            username='testteacher',
            password='testpassword',
            role=CustomUser.Role.TEACHER
        )
        self.client.login(username='testteacher', password='testpassword')
        
        # Create an existing session plan
        self.session = SessionPlan.objects.create(
            teacher=self.teacher,
            sector='ICT',
            trade='Software Development',
            level='Level 4',
            class_name='Class A',
            num_students=20,
            academic_year='2025/2026',
            term='Term 1',
            weeks='1',
            module='Module A',
            learning_outcome='Outcome A',
            indicative_content='Content A',
            topic='Initial Topic',
            objectives='Initial Objectives',
            facilitation_technique='Brainstorming',
            resources='Laptops',
            range_details='Initial Range',
            duration='60 min',
            reflection='Initial Reflection',
            references='Initial References'
        )
        
        # Create related activities
        self.act1 = Activity.objects.create(
            session=self.session,
            step_name='Intro',
            trainer_activity='Trainer Intro',
            learner_activity='Learner Intro',
            time_allocation='10 min',
            resources_needed='Board'
        )

    def test_editor_view_get(self):
        url = reverse('edit_session_plan', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Interactive Session Editor')
        self.assertContains(response, 'Initial Topic')

    def test_editor_view_post_save(self):
        url = reverse('edit_session_plan', kwargs={'session_id': self.session.id})
        post_data = {
            'sector': 'Updated Sector',
            'trade': 'Updated Trade',
            'level': 'Level 5',
            'class_name': 'Class B',
            'num_students': 25,
            'academic_year': '2026/2027',
            'term': 'Term 2',
            'weeks': '2',
            'module': 'Updated Module',
            'learning_outcome': 'Updated Outcome',
            'indicative_content': 'Updated Indicative Content',
            'performance_criteria': 'Updated PC',
            'pre_requisite_knowledge': 'Updated Prereq',
            'topic': 'Updated Topic\nStep 2',
            'range_details': 'Updated Range',
            'duration': '90 min',
            'facilitation_technique': 'Lecturing',
            'objectives': '<p>Updated Objectives</p>',
            'cross_cutting_issues': '<p>Updated CC</p>',
            'hse_considerations': '<p>Updated HSE</p>',
            'ict_tools': 'Updated ICT',
            'special_needs_support': '<p>Updated SEN</p>',
            'resources': '<p>Updated Resources</p>',
            'reflection': '<p>Updated Reflection</p>',
            'references': '<p>Updated References</p>',
            # Dynamic lists for Activities
            'step_name[]': ['Step A', 'Step B'],
            'trainer_activity[]': ['Trainer does A', 'Trainer does B'],
            'learner_activity[]': ['Learner does A', 'Learner does B'],
            'time_allocation[]': ['15 min', '20 min'],
            'resources_needed[]': ['Sheet A', 'Sheet B']
        }
        
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to dashboard
        
        # Verify db was updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.sector, 'Updated Sector')
        self.assertEqual(self.session.trade, 'Updated Trade')
        self.assertEqual(self.session.objectives, '<p>Updated Objectives</p>')
        
        # Verify related activities were re-created
        activities = self.session.activities.all().order_by('id')
        self.assertEqual(activities.count(), 2)
        self.assertEqual(activities[0].step_name, 'Step A')
        self.assertEqual(activities[0].trainer_activity, 'Trainer does A')
        self.assertEqual(activities[1].step_name, 'Step B')
        self.assertEqual(activities[1].trainer_activity, 'Trainer does B')


class ClassroomCoTeachingTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create two teachers in the same school
        self.teacher_a = CustomUser.objects.create_user(
            username='teacher_a',
            password='password123',
            role=CustomUser.Role.TEACHER,
            school_name='Centennial Academy'
        )
        self.teacher_b = CustomUser.objects.create_user(
            username='teacher_b',
            password='password123',
            role=CustomUser.Role.TEACHER,
            school_name='Centennial Academy'
        )
        
        # Create a classroom owned by teacher A
        from core.models import Classroom
        self.classroom = Classroom.objects.create(
            name='Cloud Computing L4',
            teacher=self.teacher_a
        )

    def test_send_share_request(self):
        self.client.login(username='teacher_b', password='password123')
        url = reverse('send_share_request', kwargs={'classroom_id': self.classroom.id})
        
        # POST to request access
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        
        from core.models import ClassroomShareRequest
        share_request = ClassroomShareRequest.objects.get(classroom=self.classroom, requester=self.teacher_b)
        self.assertEqual(share_request.status, 'PENDING')
        self.assertEqual(share_request.receiver, self.teacher_a)

    def test_respond_share_request_approve(self):
        # First, create a pending request
        from core.models import ClassroomShareRequest
        req = ClassroomShareRequest.objects.create(
            classroom=self.classroom,
            requester=self.teacher_b,
            receiver=self.teacher_a,
            status='PENDING'
        )
        
        # Log in as class owner (receiver)
        self.client.login(username='teacher_a', password='password123')
        url = reverse('respond_share_request', kwargs={'request_id': req.id, 'action': 'approve'})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        req.refresh_from_db()
        self.assertEqual(req.status, 'APPROVED')
        self.assertTrue(self.classroom.co_teachers.filter(id=self.teacher_b.id).exists())

    def test_respond_share_request_reject(self):
        # First, create a pending request
        from core.models import ClassroomShareRequest
        req = ClassroomShareRequest.objects.create(
            classroom=self.classroom,
            requester=self.teacher_b,
            receiver=self.teacher_a,
            status='PENDING'
        )
        
        # Log in as class owner (receiver)
        self.client.login(username='teacher_a', password='password123')
        url = reverse('respond_share_request', kwargs={'request_id': req.id, 'action': 'reject'})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        req.refresh_from_db()
        self.assertEqual(req.status, 'REJECTED')
        self.assertFalse(self.classroom.co_teachers.filter(id=self.teacher_b.id).exists())

    def test_add_co_teacher_direct(self):
        self.client.login(username='teacher_a', password='password123')
        url = reverse('add_co_teacher', kwargs={'classroom_id': self.classroom.id, 'teacher_id': self.teacher_b.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.assertTrue(self.classroom.co_teachers.filter(id=self.teacher_b.id).exists())

    def test_remove_co_teacher(self):
        # Add co-teacher first
        self.classroom.co_teachers.add(self.teacher_b)
        
        self.client.login(username='teacher_a', password='password123')
        url = reverse('remove_co_teacher', kwargs={'classroom_id': self.classroom.id, 'teacher_id': self.teacher_b.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        self.assertFalse(self.classroom.co_teachers.filter(id=self.teacher_b.id).exists())

