#-*- coding: utf-8 -*-
import collections
import os

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.files.storage import FileSystemStorage
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import detail_route

from django_filters.rest_framework import DjangoFilterBackend

from apps.thesis.models import Thesis, ThesisLog
from apps.thesis.serializers import ThesisSerializer, ThesisLogSerializer
from apps.thesis.permissions import IsOwnerOrReadOnly, can_download, can_pack
from utils.validate import validator_text
from utils.file_response import file_response, file_pack


class ThesisViewSet(viewsets.ModelViewSet):
    queryset = Thesis.objects.all()
    serializer_class = ThesisSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('stu_name', 'stu_num', 'stu_subj', 'graduation_year', 'title', 'instructor')

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
            if cache_dic['stu_subj'] == '通信工程':
                cache_dic['stu_subj'] = 'CE'
            elif cache_dic['stu_subj'] == '信息与计算科学':
                cache_dic['stu_subj'] = 'IS'
            else:
                bad_data.append(line)
                continue
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

    @detail_route()
    def thesis_log(self, request, pk=None):
        thesis_log = self.get_object().thesis_log.all()
        serializer = ThesisLogSerializer(thesis_log, many=True)
        data = collections.OrderedDict()
        data['MANDATE'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "01任务书",
            "material": "MANDATE",
            "upload_times": 0
        }
        data['SCHEDULE1'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "02指导计划表(教师)",
            "material": "SCHEDULE1",
            "upload_times": 0
        }
        data['SCHEDULE2'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "03指导计划表(学生)",
            "material": "SCHEDULE2",
            "upload_times": 0
        }
        data['PROPOSAL'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "04开题报告",
            "material": "PROPOSAL",
            "upload_times": 0
        }
        data['CHECKLIST'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "05中期检查表",
            "material": "CHECKLIST",
            "upload_times": 0
        }
        data['PPT1'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "06中期检答辩PPT",
            "material": "PPT1",
            "upload_times": 0
        }
        data['DEFENCE'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "07答辩申请表",
            "material": "DEFENCE",
            "upload_times": 0
        }
        data['ADVICE'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "08导教师意见",
            "material": "ADVICE",
            "upload_times": 0
        }
        data['REVIEW'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "09评阅意见",
            "material": "REVIEW",
            "upload_times": 0
        }
        data['THESIS'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "10论文",
            "material": "THESIS",
            "upload_times": 0
        }
        data['PPT2'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "11答辩PPT",
            "material": "PPT2",
            "upload_times": 0
        }
        data['SCORE'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "12成绩登记表",
            "material": "SCORE",
            "upload_times": 0
        }
        data['SOURCECODE'] = {
            "pk": '',
            "last_upload_time": '',
            "filename_cn": "13源代码",
            "material": "SOURCECODE",
            "upload_times": 0
        }
        for item in serializer.data:
            if item.get('last_upload_time'):
                data[item.get('file')]['last_upload_time'] = item.get('last_upload_time')
            if item.get('id'):
                data[item.get('file')]['pk'] = item.get('id')
            data[item.get('file')]['filename_cn'] = item.get('filename_cn')
            data[item.get('file')]['upload_times'] = item.get('upload_times')
        thesis_log_data = []
        for k, v in data.items():
            thesis_log_data.append(v)
        return Response({'data': thesis_log_data}, status=status.HTTP_200_OK)

    @detail_route()
    def top_5_log(self, request, pk=None):
        logs = self.get_object().thesis_log.all()
        if len(logs) <= 5:
            serializer = ThesisLogSerializer(logs, many=True)
        else:
            top_5_logs = logs[0:5]
            serializer = ThesisLogSerializer(top_5_logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)


class ThesisMaterials(APIView):
    '''
    get thesis materials choice
    post to upload material file
    '''
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        choices = []
        choices.append({
            'value': 'MANDATE',
            'filename': u'01任务书'
        })
        choices.append({
            'value': 'SCHEDULE1',
            'filename': u'02指导计划表(教师)'
        })
        choices.append({
            'value': 'SCHEDULE2',
            'filename': u'03指导计划表(学生)'
        })
        choices.append({
            'value': 'PROPOSAL',
            'filename': u'04开题报告'
        })
        choices.append({
            'value': 'CHECKLIST',
            'filename': u'05中期检查表'
        })
        choices.append({
            'value': 'PPT1',
            'filename': u'06中期检答辩PPT'
        })
        choices.append({
            'value': 'DEFENCE',
            'filename': u'07答辩申请表'
        })
        choices.append({
            'value': 'ADVICE',
            'filename': u'08导教师意见'
        })
        choices.append({
            'value': 'REVIEW',
            'filename': u'09评阅意见'
        })
        choices.append({
            'value': 'THESIS',
            'filename': u'10论文'
        })
        choices.append({
            'value': 'PPT2',
            'filename': u'11答辩PPT'
        })
        choices.append({
            'value': 'SCORE',
            'filename': u'12成绩登记表'
        })
        choices.append({
            'value': 'SOURCECODE',
            'filename': u'13源代码'
        })
        return Response(choices, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        '''
        upload materials
        '''
        # 数据初始化
        accept_type = ['png', 'jpg', 'jepg', 'pdf', 'txt',
                       'doc', 'docx', 'xls', 'xlsx', 'ppt',
                       'pptx', 'md', 'zip', 'rar', '7z',
                       'gz', 'bz2']
        data_params = request.data
        file = request.FILES['my_file']
        thesis_obj = get_object_or_404(Thesis, id=data_params['thesis_id'])
        user = request.user
        # 用户权限判断
        if not user == thesis_obj.instructor:
            return Response({'msg': u'只有指导老师本人可以上传材料！'}, status=status.HTTP_403_FORBIDDEN)
        # 验证文件类型
        file_type = str(file.name).split('.',)[-1]
        if not file_type in accept_type:
            return Response({'msg': u'只允许上传图片，word文档，文本文档，markdown文档，幻灯片文档，excel文档以及压缩包！'}, status=status.HTTP_400_BAD_REQUEST)
        # 按照model中的file_path保存文件,并重命名文件。
        with transaction.atomic():
            thesis_log_obj = ThesisLog.objects.get_or_create(thesis=thesis_obj, file=data_params['material'])[0]
            thesis_log_obj.upload_times += 1
            # 删除原先的文件
            if os.path.exists(thesis_log_obj.file_abs_path):
                os.remove(thesis_log_obj.file_abs_path)
            file_name = u'{}.{}'.format(thesis_log_obj.filename_cn, file_type)
            file_save_path = os.path.join(thesis_obj.file_path, file_name)
            thesis_log_obj.file_abs_path = file_save_path
            fs = FileSystemStorage()
            fs.save(file_save_path, file)
            thesis_log_obj.save()
            return Response(status=status.HTTP_200_OK)


class GetMaterial(APIView):
    '''
    download a material file
    '''
    def get(self, request, format=None):
        # 数据初始化
        data_params = request.GET
        material_obj = get_object_or_404(ThesisLog, id=data_params['thesis_log_id'])
        file_path = material_obj.file_abs_path
        filename_cn = os.path.basename(file_path)
        # 权限判断
        if not can_download(request.user, material_obj):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # 调用util中的函数返回文件
        response = file_response(file_path=file_path, filename=filename_cn)
        if response:
            return response
        return Response({'msg': u'文件不存在！'}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request, format=None):
        data_params = request.data
        material_obj = get_object_or_404(ThesisLog, id=data_params['thesis_log_id'])
        file_path = material_obj.file_abs_path
        filename_cn = os.path.basename(file_path)
        return Response({'filename': filename_cn}, status=status.HTTP_200_OK)

class GetMaterials(APIView):
    '''
    download all material zip
    '''
    def get(self, request, format=None):
        # 数据初始化
        data_params = request.GET
        user = request.user
        thesis_obj = get_object_or_404(Thesis, id=data_params['thesis_id'])
        file_path = thesis_obj.file_path
        zip_name = u'{}.zip'.format(str(file_path).split('/',)[-1])
        output_filename = os.path.join(file_path, zip_name)
        # 权限判断
        if not can_pack(user, thesis_obj):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # 删除原有的zip文件
        if os.path.isfile(output_filename):
            os.remove(output_filename)
        # 文件打包
        try:
            file_pack(file_path=file_path, output_filename=output_filename)
        except Exception as e:
            return Response({'msg': u'文件打包失败！'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 调用util中的函数返回文件
        response = file_response(file_path=output_filename, filename=zip_name)
        if response:
            return response
        return Response({'msg': u'文件不存在！'}, status=status.HTTP_400_BAD_REQUEST)
