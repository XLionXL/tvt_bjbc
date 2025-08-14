//
// Created by admins on 2023/6/28.
//
#include <stdbool.h>

bool inside(float poi_x, float poi_y,int polyNum,float poly[][2]){
    int in_cnt=0;
    int neighbor;
    float start_poi_x,start_poi_y,  end_poi_x, end_poi_y;
    for (int i = 0; i < polyNum; i++) {
        neighbor = (i + 1) % polyNum;
        start_poi_x = poly[i][0];
        start_poi_y = poly[i][1];
        end_poi_x = poly[neighbor][0];
        end_poi_y = poly[neighbor][1];
        if (((start_poi_y > poi_y) != (end_poi_y > poi_y)) && (poi_x < ((end_poi_x - start_poi_x) * (poi_y - start_poi_y) / (end_poi_y - start_poi_y) + start_poi_x))){
            in_cnt += 1;
        }
    }
    return (in_cnt % 2 == 1);
}