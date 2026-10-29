import os
import sys

# Ensure scoop shims (where dot.exe is located) is in PATH
scoop_shims = r"C:\Users\Miyanber\scoop\shims"
if scoop_shims not in os.environ.get("PATH", ""):
    os.environ["PATH"] = scoop_shims + os.pathsep + os.environ.get("PATH", "")

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.saas.cdn import Cloudflare
from diagrams.aws.compute import EC2, EC2ElasticIpAddress
from diagrams.aws.storage import S3
from diagrams.aws.security import IAM
from diagrams.onprem.network import Nginx
from diagrams.programming.framework import Django
from diagrams.onprem.inmemory import Redis
from diagrams.generic.database import SQL

graph_attr = {
    "fontsize": "18",
    "fontname": "Helvetica",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
}

node_attr = {
    "fontname": "Helvetica",
    "fontsize": "12",
}

output_path = os.path.join(os.getcwd(), "docs", "images", "architecture")

with Diagram(
    name="RakuNavi Infrastructure Architecture",
    filename=output_path,
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    users = Users("Users\n(Visitors & Students)")

    with Cluster("Cloudflare (Edge Services)", graph_attr={"bgcolor": "#FBF5E8", "color": "#F38020"}):
        cf = Cloudflare("Cloudflare\n(CDN & Security)")

    with Cluster("AWS Cloud (Tokyo: ap-northeast-1)", graph_attr={"bgcolor": "#F7F9FA", "color": "#232F3E"}):

        with Cluster("Amazon VPC (Virtual Network)", graph_attr={"bgcolor": "#EDF4F9", "color": "#147EBA"}):
            eip = EC2ElasticIpAddress("Elastic IP\n(Static IP)")

            with Cluster("Amazon EC2 (Server: t3.micro)", graph_attr={"bgcolor": "#FFFFFF", "color": "#D05C17"}):
                ec2_inst = EC2("EC2 (Ubuntu)")
                nginx = Nginx("Nginx\n(Web Server)")
                django = Django("Django\n(Web App)")
                redis = Redis("Redis\n(Cache & Tasks)")
                db = SQL("SQLite\n(Database)")

                nginx >> Edge(label="Forward") >> django
                django - Edge(style="dotted") - ec2_inst
                django >> Edge(label="Live Updates") >> redis
                django >> Edge(label="Read / Write") >> db

        with Cluster("Storage & Permissions", graph_attr={"bgcolor": "#EDF4F9", "color": "#3B48CC"}):
            s3 = S3("Amazon S3\n(Images & Static Files)")
            iam = IAM("IAM\n(Access Control)")
            django >> Edge(label="Upload Media") >> iam >> s3

    # Main user traffic flow (Web app access)
    users >> Edge(label="Page View & Status Updates", color="#1E88E5", style="bold") >> cf
    cf >> Edge(label="Forward Request", color="#1E88E5", style="bold") >> eip >> nginx

    # Static / Media delivery flow (Fast CDN cache)
    users >> Edge(label="Images & Styles", color="#FF8F00", style="dashed") >> cf
    cf >> Edge(label="Fetch Media", color="#FF8F00", style="dashed") >> s3

print(f"Generated architecture diagram at {output_path}.png")
