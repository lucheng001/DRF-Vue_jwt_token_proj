#-*- coding: utf-8 -*-

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.thesis.models import Thesis
from apps.thesis.serializers import ThesisSerializer
from apps.thesis.permissions import IsOwnerOrReadOnly
from utils.validate import validator_text


class ThesisViewSet(viewsets.ModelViewSet):
    queryset = Thesis.objects.all()
    serializer_class = ThesisSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

    def get_queryset(self):
        if self.request.user.user_info.role == 'admin' or self.request.user.user_info.role == 'college_leader':
            return Thesis.objects.all()
        elif self.request.user.user_info.role == 'subject_leader':
            try:
                dep = self.request.user.user_info.job.split('_',)[0]
                return Thesis.objects.filter(Q(stu_subj=dep) | Q(instructor=self.request.user))
            except Exception as e:
                return self.request.user.thesis.all()
        return self.request.user.thesis.all()

    def create(self, request, *args, **kwargs):
        data = request.data.get('data')
        lines = data.splitlines()
        good_data = []
        bad_data = []
        for line in lines:
            # 验证数据是否合理
            if len(line.split(',',)) != 5:
                bad_data.append(line)
                continue

            if not validator_text(line):
                bad_data.append(line)
                print(u'有特殊字符')
                continue

            cache_dic = {}
            cache_dic['stu_name'], cache_dic['stu_num'], \
            cache_dic['stu_subj'], cache_dic['graduation_year'], \
            cache_dic['title'] = line.split(',',)
            cache_dic['instructor'] = request.user
            # 判断该学生论文数据是否已经存在
            if Thesis.objects.filter(stu_num=cache_dic['stu_num']):
                bad_data.append(line)
                continue

            try:
                thesis = Thesis(**cache_dic)
                thesis.save()
                good_data.append(line)
            except Exception as e:
                bad_data.append(line)

        return Response({'success': len(good_data), 'failed': len(bad_data)}, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

