import { admissionsV1En } from "./admissions-v1.en";

export const admissionsV1UzLatn = {
  ...admissionsV1En,
  "admissions.proposals.title": "Jonli qabul tavsiyalari",
  "admissions.classes.add": "Kursni qo‘shish",
  "admissions.classes.added": "Qo‘shildi",
  "admissions.assessment.title": "Mutaxassislik va kasb qiziqish testi",
  "admissions.assessment.next": "Keyingi bo‘lim",
  "admissions.assessment.previous": "Oldingi bo‘lim",
  "admissions.assessment.results": "Tavsiyalarni ko‘rish",
  "admissions.assessment.use": "Tanlangan tavsiyalardan foydalanish",
  "admissions.country.title": "Maqsad mamlakatlar",
  "admissions.readiness.title": "Ariza tayyorligi",
  "admissions.readiness.description": "Profil dalillari va e'lon qilingan talab diapazonlarining tuzilgan ko'rib chiqilishi.",
  "admissions.readiness.disclaimer": "Tayyorlik mavjud profil ma'lumotlari va mavjud bo'lsa e'lon qilingan diapazonlarga asoslangan axborot taqqoslashidir.",
  "admissions.component.leadership": "Liderlik",
  "admissions.component.honors": "Mukofotlar va yutuqlar",
  "admissions.component.olympiads": "Olimpiadalar va tanlovlar",
  "admissions.component.sports": "Sport",
  "admissions.component.research": "Tadqiqot",
  "admissions.component.portfolio": "Portfolio va loyihalar",
  "admissions.component.volunteering": "Volontyorlik va jamiyat",
  "admissions.component.recommenders": "Tavsiya xatlari",
  "dashboard.learning.title": "Tavsiya etilgan o‘qish yo‘li",
  "events.map.title": "Imkoniyatlar xaritasi"
} satisfies Record<keyof typeof admissionsV1En, string>;
