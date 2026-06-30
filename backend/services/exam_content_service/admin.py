from django.contrib import admin

from .models import AnswerChoice, Exam, ExamSection, Explanation, OfficialExamDate, Question

admin.site.register(Exam)
admin.site.register(ExamSection)
admin.site.register(Question)
admin.site.register(AnswerChoice)
admin.site.register(Explanation)
admin.site.register(OfficialExamDate)
