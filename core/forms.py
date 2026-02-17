from django import forms
from .models import SessionPlan, Activity
from django.forms import inlineformset_factory

class SessionPlanForm(forms.ModelForm):
    class Meta:
        model = SessionPlan
        fields = [
            'sector', 'trade', 'module', 'learning_outcome', 
            'topic', 'objectives', 'facilitation_technique', 
            'resources', 'range_details', 'duration'
        ]
        widgets = {
            'sector': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'trade': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'module': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'learning_outcome': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'rows': 3}),
            'topic': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'objectives': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'rows': 3}),
            'facilitation_technique': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'resources': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'rows': 3}),
            'range_details': forms.Textarea(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline', 'rows': 2}),
            'duration': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }

ActivityFormSet = inlineformset_factory(
    SessionPlan, Activity,
    fields=['step_name', 'trainer_activity', 'learner_activity', 'time_allocation', 'resources_needed'],
    extra=3,
    can_delete=True,
    widgets={
        'step_name': forms.TextInput(attrs={'class': 'form-input block w-full sm:text-sm border-gray-300 rounded-md', 'placeholder': 'Step Name'}),
        'trainer_activity': forms.Textarea(attrs={'class': 'form-textarea block w-full sm:text-sm border-gray-300 rounded-md', 'rows': 2, 'placeholder': 'Trainer Activity'}),
        'learner_activity': forms.Textarea(attrs={'class': 'form-textarea block w-full sm:text-sm border-gray-300 rounded-md', 'rows': 2, 'placeholder': 'Learner Activity'}),
        'time_allocation': forms.TextInput(attrs={'class': 'form-input block w-full sm:text-sm border-gray-300 rounded-md', 'placeholder': 'Time'}),
        'resources_needed': forms.Textarea(attrs={'class': 'form-textarea block w-full sm:text-sm border-gray-300 rounded-md', 'rows': 2, 'placeholder': 'Resources'}),
    }
)

from .models import StudentMark, CustomUser, Assessment

class TeacherMarksForm(forms.ModelForm):
    # Field to create a new assessment title on the fly or select existing could be complex.
    # For now, let's keep it simple: Teacher enters a title (creating a new Assessment implicitly or selecting one)
    # But to stick to the prompt's "Simple Database Schema", we'll just allow creating an assessment title here.
    assessment_title = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    
    class Meta:
        model = StudentMark
        fields = ['student', 'score', 'total_marks']
        widgets = {
            'student': forms.Select(attrs={'class': 'block appearance-none w-full bg-white border border-gray-400 hover:border-gray-500 px-4 py-2 pr-8 rounded shadow leading-tight focus:outline-none focus:shadow-outline'}),
            'score': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'total_marks': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter students only
        self.fields['student'].queryset = CustomUser.objects.filter(role=CustomUser.Role.STUDENT)

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['module', 'assessment_type', 'title', 'total_marks']
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter modules by teacher
        if user:
            from .models import Module
            self.fields['module'].queryset = Module.objects.filter(teacher=user)

class StudentMarkForm(forms.ModelForm):
    class Meta:
        model = StudentMark
        fields = ['score']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['score'].widget.attrs.update({'class': 'shadow appearance-none border rounded w-full py-1 px-2 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'})

StudentMarkFormSet = forms.modelformset_factory(
    StudentMark,
    form=StudentMarkForm,
    extra=0,
)
