#!/usr/bin/python
#################################################################
##\file
#
# \note
# Copyright (c) 2010 \n
# Fraunhofer Institute for Manufacturing Engineering
# and Automation (IPA) \n\n
#
#################################################################
#
# \note
# Project name: Care-O-bot Research
# \note
# ROS stack name: cob_environments
# \note
# ROS package name: cob_gazebo_objects
#
# \author
# Author: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
# \author
# Supervised by: Florian Weisshardt, email:florian.weisshardt@ipa.fhg.de
#
# \date Date of creation: Feb 2012
#
# \brief
# Implements script server functionalities.
#
#################################################################
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer. \n
# - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. \n
# - Neither the name of the Fraunhofer Institute for Manufacturing
# Engineering and Automation (IPA) nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission. \n
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License LGPL as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License LGPL for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License LGPL along with this program.
# If not, see < http://www.gnu.org/licenses/>.
#
#################################################################
import sys

import rospy
import copy
import math
from gazebo_msgs.srv import DeleteModel, DeleteModelRequest
import tf.transformations as tft

parents = {}
compound_keys={}

def get_flat_dict(objects, parent_name):
    """expands all objects to a flat dictionary"""
    flat_objects = {}
    for key, value in objects.iteritems():
        # check if we have an atomic object

        if(parent_name!=None):
            
            if('parent_name' not in parents):
                parents[key] = parent_name

                compound_keys[parent_name] = parent_name

            compound_keys[key] = key+'_'+compound_keys[parent_name]

        else:
            compound_keys[key] = key

        if "children" in value:
            # add parent object without children to flat_objects
            tmp_value = copy.deepcopy(value)
            to_process = tmp_value["children"]

            # add position and orientation of parent to all children
            for child_key, child_value in tmp_value["children"].iteritems():
                yaw = objects[key]["orientation"][2]
                x = objects[key]["position"][0] + math.cos(yaw) * child_value["position"][0] - math.sin(yaw) * child_value["position"][1]
                y = objects[key]["position"][1] + math.sin(yaw) * child_value["position"][0] + math.cos(yaw) * child_value["position"][1]
                child_value["position"][0] = x
                child_value["position"][1] = y
                child_value["position"][2] = objects[key]["position"][2] + child_value["position"][2]
                child_value["orientation"][2] = yaw + child_value["orientation"][2]
            del tmp_value["children"]
            flat_objects.update({compound_keys[key]:tmp_value})
            # add flattened children to flat_objects
            flat_objects.update(get_flat_dict(to_process, compound_keys[key]))

        else:
            # add object to flat_objects
            flat_objects.update({compound_keys[key]:value})

    return flat_objects

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print '[remove_object.py] Please specify the names of the objects to be removed'
        sys.exit()

    rospy.init_node("object_remover")

    # check for all objects on parameter server
    if not rospy.has_param("/objects"):
        rospy.logerr("No objects uploaded to /objects")
        sys.exit()
    objects = rospy.get_param("/objects")
    flat_objects = get_flat_dict(objects,None)

    # check for all object groups on parameter server
    if rospy.has_param("/object_groups"):
        groups = rospy.get_param("/object_groups")
    else:
        groups = {}
        rospy.loginfo('No object-groups uploaded to /object_groups')

    # if keyword all is in list of object names we'll load all models uploaded to parameter server
    if "all" in sys.argv:
        objects = flat_objects
    elif not set(groups.keys()).isdisjoint(sys.argv):
        # get all key that are in both, the dictionary and argv
        found_groups = set(groups.keys()) & set(sys.argv)
        # get all object_names from keys that are in argv
        object_names = [groups[k] for k in found_groups]
        # flatten list of lists 'object_names' to a list
        object_names = [item for sublist in object_names for item in sublist]
        # save all dict-objects with names in 'object_names' in 'objects'
        objects = {}
        for object_name in object_names:
            if object_name in flat_objects.keys():
                objects.update({object_name:flat_objects[object_name]})
    elif sys.argv[1] not in flat_objects.keys():
        rospy.logerr("Object %s not found", sys.argv[1])
        sys.exit()
    else:
        objects = {sys.argv[1]:flat_objects[sys.argv[1]]}

    rospy.loginfo("Trying to remove %s", objects.keys())

    for name in objects:
        # check if object is already spawned
        srv_delete_model = rospy.ServiceProxy('gazebo/delete_model', DeleteModel)
        req = DeleteModelRequest()
        req.model_name = name
        exists = True
        try:
            rospy.wait_for_service('/gazebo/delete_model')
            res = srv_delete_model(name)
        except rospy.ServiceException, e:
            exists = False
            rospy.logdebug("Model %s does not exist in gazebo.", name)

        if exists:
            rospy.loginfo("Model %s removed.", name)
        else:
            rospy.logerr("Model %s not found in gazebo.", name)
